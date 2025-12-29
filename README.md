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

## License

MIT
