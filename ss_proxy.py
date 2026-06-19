#!/usr/bin/env python3
"""Minimal pure-Python Shadowsocks (AEAD) -> local SOCKS5 proxy.

Implements the Shadowsocks AEAD TCP protocol for chacha20-ietf-poly1305 and
exposes it as a standard SOCKS5 CONNECT proxy on a local port, so you can test
an ss:// access key with any normal client (curl, browser, etc.).

Usage:
    python3 ss_proxy.py 'ss://<base64>@host:port/?outline=1' --listen 127.0.0.1:1080
"""
import argparse
import base64
import hashlib
import os
import socket
import struct
import sys
import threading
from urllib.parse import urlparse

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

KEY_LEN = 32      # chacha20-ietf-poly1305
SALT_LEN = 32
NONCE_LEN = 12
TAG_LEN = 16
MAX_PAYLOAD = 0x3FFF


def evp_bytes_to_key(password: bytes, key_len: int) -> bytes:
    """Derive the master key from the password (OpenSSL EVP_BytesToKey, MD5)."""
    m, prev = b"", b""
    while len(m) < key_len:
        prev = hashlib.md5(prev + password).digest()
        m += prev
    return m[:key_len]


def hkdf_subkey(key: bytes, salt: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA1(), length=KEY_LEN, salt=salt,
                info=b"ss-subkey").derive(key)


class AEAD:
    """One direction of an AEAD stream (its own salt-derived subkey + nonce)."""
    def __init__(self, key: bytes, salt: bytes):
        self.cipher = ChaCha20Poly1305(hkdf_subkey(key, salt))
        self.counter = 0

    def _nonce(self) -> bytes:
        n = self.counter.to_bytes(NONCE_LEN, "little")
        self.counter += 1
        return n

    def encrypt(self, data: bytes) -> bytes:
        return self.cipher.encrypt(self._nonce(), data, None)

    def decrypt(self, data: bytes) -> bytes:
        return self.cipher.decrypt(self._nonce(), data, None)


def recv_all(sock: socket.socket, n: int):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def encrypt_payload(enc: AEAD, data: bytes) -> bytes:
    """Encrypt a plaintext blob into one or more SS AEAD length-prefixed chunks."""
    out = b""
    for i in range(0, len(data), MAX_PAYLOAD):
        chunk = data[i:i + MAX_PAYLOAD]
        out += enc.encrypt(struct.pack(">H", len(chunk)))  # encrypted length
        out += enc.encrypt(chunk)                           # encrypted payload
    return out


def read_chunk(remote: socket.socket, dec: AEAD):
    """Read & decrypt one SS AEAD chunk from the server. None on EOF."""
    enc_len = recv_all(remote, 2 + TAG_LEN)
    if enc_len is None:
        return None
    length = struct.unpack(">H", dec.decrypt(enc_len))[0]
    enc_payload = recv_all(remote, length + TAG_LEN)
    if enc_payload is None:
        return None
    return dec.decrypt(enc_payload)


def read_socks5_target(client: socket.socket):
    """Complete the SOCKS5 handshake and return the target in SS address format."""
    greeting = recv_all(client, 2)
    if not greeting or greeting[0] != 0x05:
        return None
    recv_all(client, greeting[1])            # methods
    client.sendall(b"\x05\x00")              # no auth

    hdr = recv_all(client, 4)
    if not hdr or hdr[1] != 0x01:            # only CONNECT
        client.sendall(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
        return None
    atyp = hdr[3]
    if atyp == 0x01:
        raw = recv_all(client, 4)
        target = b"\x01" + raw
    elif atyp == 0x03:
        ln = recv_all(client, 1)
        raw = recv_all(client, ln[0])
        target = b"\x03" + ln + raw
    elif atyp == 0x04:
        raw = recv_all(client, 16)
        target = b"\x04" + raw
    else:
        return None
    port = recv_all(client, 2)
    client.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")  # success
    return target + port


def pipe_client_to_remote(client, remote, enc):
    try:
        while True:
            data = client.recv(4096)
            if not data:
                break
            remote.sendall(encrypt_payload(enc, data))
    except Exception:
        pass
    finally:
        for s in (client, remote):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def pipe_remote_to_client(client, remote, key):
    try:
        rsalt = recv_all(remote, SALT_LEN)   # server salt arrives with its first response
        if rsalt is None:
            return
        dec = AEAD(key, rsalt)
        while True:
            data = read_chunk(remote, dec)
            if not data:
                break
            client.sendall(data)
    except Exception:
        pass
    finally:
        for s in (client, remote):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def handle(client, key, server_host, server_port):
    remote = None
    try:
        target = read_socks5_target(client)
        if target is None:
            return
        remote = socket.create_connection((server_host, server_port), timeout=15)
        remote.settimeout(None)
        salt = os.urandom(SALT_LEN)
        enc = AEAD(key, salt)
        remote.sendall(salt + encrypt_payload(enc, target))  # salt + target header
        t = threading.Thread(target=pipe_remote_to_client,
                             args=(client, remote, key), daemon=True)
        t.start()
        pipe_client_to_remote(client, remote, enc)
        t.join()
    except Exception as e:
        sys.stderr.write(f"[conn error] {e}\n")
    finally:
        for s in (client, remote):
            if s:
                try:
                    s.close()
                except OSError:
                    pass


def parse_ss(url: str):
    u = urlparse(url)
    userinfo, hostport = u.netloc.split("@")
    host, port = hostport.rsplit(":", 1)
    pad = "=" * (-len(userinfo) % 4)
    decoded = base64.urlsafe_b64decode(userinfo + pad)
    method, password = decoded.split(b":", 1)
    return method.decode(), password, host, int(port)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ss_url")
    ap.add_argument("--listen", default="127.0.0.1:1080")
    args = ap.parse_args()

    method, password, server_host, server_port = parse_ss(args.ss_url)
    if method != "chacha20-ietf-poly1305":
        sys.exit(f"Only chacha20-ietf-poly1305 implemented, got: {method}")
    key = evp_bytes_to_key(password, KEY_LEN)

    lhost, lport = args.listen.rsplit(":", 1)
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((lhost, int(lport)))
    srv.listen(128)
    print(f"LISTENING SOCKS5 {lhost}:{lport} -> {server_host}:{server_port} "
          f"({method})", flush=True)
    while True:
        client, _ = srv.accept()
        threading.Thread(target=handle,
                         args=(client, key, server_host, server_port),
                         daemon=True).start()


if __name__ == "__main__":
    main()
