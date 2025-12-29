# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Single-file Python CLI for managing Outline VPN access keys via the Outline Server API.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install outline-vpn-api python-dotenv
```

First run prompts for credentials, saved to `.env`:
```
OUTLINE_API_URL=https://x.x.x.x:port/prefix
OUTLINE_CERT_SHA256=xxxx...
```

## CLI Commands

```bash
python outline_cli.py list                    # List all keys
python outline_cli.py show <key_id>           # Show full key details
python outline_cli.py add [--name NAME]       # Create new key
python outline_cli.py delete <key_id>         # Delete key
python outline_cli.py rename <key_id> <name>  # Rename key
python outline_cli.py limit <key_id> <mb>     # Set data limit (0 to remove)
```

## Code Structure

- `outline_cli.py` - Single file containing all logic
  - Config functions: `load_config()`, `setup_config()`, `get_client()`
  - Command handlers: `cmd_list()`, `cmd_show()`, `cmd_add()`, `cmd_delete()`, `cmd_rename()`, `cmd_limit()`
  - CLI setup via argparse subparsers in `main()`

## Key Implementation Notes

- Import path for outline-vpn-api: `from outline_vpn.outline_vpn import OutlineVPN`
- API key IDs may be strings; compare with `str(k.key_id) == str(key_id)`
- Data usage/limits are in bytes; convert to/from MB for display
