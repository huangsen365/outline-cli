#!/usr/bin/env python3
"""Single-shot Shadowsocks (AEAD) connectivity test.

Tunnels one HTTP/1.0 request through an Outline/Shadowsocks server using the
chacha20-ietf-poly1305 AEAD protocol and prints each step, so you can confirm
an ss:// key actually works (handshake, encryption, relay) without any client.

Usage:
    python3 ss_test.py 'ss://<base64>@host:port/?outline=1'
    python3 ss_test.py 'ss://...' --target ifconfig.me:80 --path /ip
"""
import argparse
import base64
import hashlib
import os
import socket
import struct
import sys
from urllib.parse import urlparse

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

KEY_LEN = SALT_LEN = 32
NONCE_LEN = 12
TAG_LEN = 16


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
    def __init__(self, key: bytes, salt: bytes):
        self.c = ChaCha20Poly1305(hkdf_subkey(key, salt))
        self.n = 0

    def _nonce(self) -> bytes:
        v = self.n.to_bytes(NONCE_LEN, "little")
        self.n += 1
        return v

    def enc(self, d: bytes) -> bytes:
        return self.c.encrypt(self._nonce(), d, None)

    def dec(self, d: bytes) -> bytes:
        return self.c.decrypt(self._nonce(), d, None)


def recv_all(s: socket.socket, n: int):
    b = b""
    while len(b) < n:
        c = s.recv(n - len(b))
        if not c:
            return None
        b += c
    return b


def enc_payload(a: AEAD, data: bytes) -> bytes:
    return a.enc(struct.pack(">H", len(data))) + a.enc(data)


def parse_ss(url: str):
    u = urlparse(url)
    userinfo, hostport = u.netloc.split("@")
    host, port = hostport.rsplit(":", 1)
    decoded = base64.urlsafe_b64decode(userinfo + "=" * (-len(userinfo) % 4))
    method, password = decoded.split(b":", 1)
    return method.decode(), password, host, int(port)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ss_url", help="ss://<base64>@host:port/?outline=1")
    ap.add_argument("--target", default="api.ipify.org:80",
                    help="host:port to fetch through the tunnel (default api.ipify.org:80)")
    ap.add_argument("--path", default="/", help="HTTP path to GET (default /)")
    args = ap.parse_args()

    method, password, server_host, server_port = parse_ss(args.ss_url)
    if method != "chacha20-ietf-poly1305":
        sys.exit(f"Only chacha20-ietf-poly1305 implemented, got: {method}")
    thost, tport = args.target.rsplit(":", 1)
    thost_b, tport = thost.encode(), int(tport)

    key = evp_bytes_to_key(password, KEY_LEN)
    print(f"server:     {server_host}:{server_port} ({method})")
    print(f"target:     {thost}:{tport}{args.path}")
    print(f"master key: {key.hex()}")

    target = b"\x03" + bytes([len(thost_b)]) + thost_b + struct.pack(">H", tport)
    http = (f"GET {args.path} HTTP/1.0\r\nHost: {thost}\r\n"
            f"User-Agent: ss-test\r\nConnection: close\r\n\r\n").encode()

    s = socket.create_connection((server_host, server_port), timeout=15)
    print("connected to server")

    salt = os.urandom(SALT_LEN)
    e = AEAD(key, salt)
    s.sendall(salt + enc_payload(e, target) + enc_payload(e, http))
    print(f"sent salt + target({len(target)}B) + http({len(http)}B)")

    rsalt = recv_all(s, SALT_LEN)
    print(f"recv server salt: {rsalt.hex() if rsalt else None}")
    if not rsalt:
        sys.exit("FAIL: no server salt -> server closed/reset before responding "
                 "(bad key/cipher or server down)")

    d = AEAD(key, rsalt)
    out = b""
    while True:
        try:
            enc_len = recv_all(s, 2 + TAG_LEN)
            if enc_len is None:
                break
            length = struct.unpack(">H", d.dec(enc_len))[0]
            enc_pl = recv_all(s, length + TAG_LEN)
            if enc_pl is None:
                print("EOF mid-chunk")
                break
            out += d.dec(enc_pl)
        except Exception as ex:
            sys.exit(f"FAIL: decrypt error {type(ex).__name__}: {ex} "
                     "(key/cipher mismatch)")

    print("=== tunneled response ===")
    print(out.decode(errors="replace"))


if __name__ == "__main__":
    main()
