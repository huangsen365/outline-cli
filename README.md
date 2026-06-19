[English](README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md)

# Outline VPN CLI

A simple command-line tool for managing Outline VPN access keys via the Outline Server API.

## Installation

```bash
# Clone the repository
git clone https://github.com/huangsen365/outline-cli.git
cd outline-cli

# Set up virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install outline-vpn-api python-dotenv

# Optional: only needed for the access-key test tools (ss_test.py / ss_proxy.py)
pip install cryptography
```

## Configuration

On first run, the CLI will prompt for your Outline server credentials:

- **API URL**: Found in your Outline Manager (e.g., `https://x.x.x.x:port/prefix`)
- **Certificate SHA256**: The certificate fingerprint from your Outline Manager

Credentials are saved to `.env` file for future use.

## Usage

```bash
# List all access keys
python outline_cli.py list

# Show full details of a specific key
python outline_cli.py show <key_id>

# Create a new access key
python outline_cli.py add
python outline_cli.py add --name "My Device"

# Delete an access key
python outline_cli.py delete <key_id>

# Rename an access key
python outline_cli.py rename <key_id> "New Name"

# Set data limit (in MB, use 0 to remove limit)
python outline_cli.py limit <key_id> 1024
python outline_cli.py limit <key_id> 0
```

## Example Output

```
$ python outline_cli.py list
ID     Name                 Usage (MB)   Access URL
--------------------------------------------------------------------------------
1      Device-A             125.3        ss://Y2hhY...@1.2.3.4:12345/?outline=1
2      Device-B             0.0          ss://Y2hhY...@1.2.3.4:12345/?outline=1
```

## Testing Access Keys

Two helper scripts verify that an `ss://` key actually works. Both take the
access URL as an argument, support the `chacha20-ietf-poly1305` cipher used by
Outline, and require the `cryptography` package (`pip install cryptography`).

```bash
# One-shot connectivity check: tunnels a single HTTP request through the key
# and prints each protocol step (handshake, encryption, response).
python ss_test.py 'ss://<base64>@host:port/?outline=1'

# Expose the key as a local SOCKS5 proxy so any client can route through it.
python ss_proxy.py 'ss://<base64>@host:port/?outline=1' --listen 127.0.0.1:1080
curl --socks5-hostname 127.0.0.1:1080 https://api.ipify.org
```

## Clash Config Template

A ready-to-fill Clash proxy template is included at
[`clash-template.yaml`](clash-template.yaml). Copy it, replace the `<...>`
placeholders with values from your access key, and load it in your Clash client.

Get a key's `ss://` access URL:

```bash
python outline_cli.py --profile <profile> show <key_id>
```

The URL has the form `ss://<base64>@<server>:<port>/?outline=1`. Decode the
`<base64>` part to reveal `<cipher>:<password>`:

```bash
echo '<base64>' | base64 -d
# -> chacha20-ietf-poly1305:<password>
```

A filled-in example:

```yaml
proxies:
  - name: "clash-mi-on-mba-m4-jp"
    type: ss
    server: example.wansio.com
    port: 2132
    cipher: chacha20-ietf-poly1305
    password: "your-password-here"
    udp: true

proxy-groups:
  - name: "Proxy"
    type: select
    proxies:
      - "clash-mi-on-mba-m4-jp"
      - DIRECT

rules:
  - GEOIP,LAN,DIRECT
  - GEOIP,CN,DIRECT
  - MATCH,Proxy
```

> **Note:** a filled config contains your key's password. Keep it out of version
> control — the `.gitignore` ignores `clash-*.yaml` (except the template itself).

## License

MIT
