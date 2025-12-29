#!/usr/bin/env python3
"""Minimal CLI for managing Outline VPN access keys."""

import argparse
import os
import sys
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"


def check_dependencies():
    """Check and import required packages."""
    try:
        from dotenv import load_dotenv
        from outline_vpn.outline_vpn import OutlineVPN
        return load_dotenv, OutlineVPN
    except ImportError as e:
        print("Missing dependencies. Install with:")
        print("  pip install outline-vpn-api python-dotenv")
        sys.exit(1)


def load_config():
    """Load config from .env file."""
    load_dotenv, _ = check_dependencies()
    if not ENV_FILE.exists():
        return None, None
    load_dotenv(ENV_FILE)
    return os.getenv("OUTLINE_API_URL"), os.getenv("OUTLINE_CERT_SHA256")


def setup_config():
    """Prompt user for config and save to .env."""
    print("First-time setup: Enter your Outline server credentials")
    print()
    api_url = input("API URL (e.g., https://x.x.x.x:port/prefix): ").strip()
    cert_sha256 = input("Certificate SHA256: ").strip()

    if not api_url or not cert_sha256:
        print("Error: Both values are required")
        sys.exit(1)

    with open(ENV_FILE, "w") as f:
        f.write(f"OUTLINE_API_URL={api_url}\n")
        f.write(f"OUTLINE_CERT_SHA256={cert_sha256}\n")

    print(f"Config saved to {ENV_FILE}")
    return api_url, cert_sha256


def get_client():
    """Get configured Outline client."""
    _, OutlineVPN = check_dependencies()
    api_url, cert_sha256 = load_config()

    if not api_url or not cert_sha256:
        api_url, cert_sha256 = setup_config()

    return OutlineVPN(api_url=api_url, cert_sha256=cert_sha256)


def cmd_list(client):
    """List all access keys."""
    try:
        keys = client.get_keys()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not keys:
        print("No access keys found")
        return

    # Print header
    print(f"{'ID':<6} {'Name':<20} {'Usage (MB)':<12} Access URL")
    print("-" * 80)

    for key in keys:
        key_id = key.key_id
        name = key.name or "(unnamed)"
        # Usage is in bytes, convert to MB
        usage_bytes = key.used_bytes or 0
        usage_mb = usage_bytes / (1024 * 1024)
        access_url = key.access_url or ""

        # Truncate long values
        if len(name) > 18:
            name = name[:17] + "…"
        if len(access_url) > 40:
            access_url = access_url[:37] + "..."

        print(f"{key_id:<6} {name:<20} {usage_mb:<12.1f} {access_url}")


def cmd_show(client, key_id):
    """Show full details for a key."""
    try:
        keys = client.get_keys()
        key = next((k for k in keys if str(k.key_id) == str(key_id)), None)
        if not key:
            print(f"Key not found: {key_id}")
            sys.exit(1)

        usage_bytes = key.used_bytes or 0
        usage_mb = usage_bytes / (1024 * 1024)

        print(f"ID:         {key.key_id}")
        print(f"Name:       {key.name or '(unnamed)'}")
        print(f"Usage:      {usage_mb:.1f} MB")
        print(f"Access URL: {key.access_url}")


    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_add(client, name):
    """Create a new access key."""
    try:
        key = client.create_key(key_name=name) if name else client.create_key()
        print(f"Created key: {key.key_id} - {key.name or '(unnamed)'}")
        print(f"Access URL: {key.access_url}")
    except Exception as e:
        print(f"Error creating key: {e}")
        sys.exit(1)


def cmd_delete(client, key_id):
    """Delete an access key."""
    try:
        result = client.delete_key(key_id)
        if result:
            print(f"Deleted key: {key_id}")
        else:
            print(f"Failed to delete key: {key_id}")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_rename(client, key_id, new_name):
    """Rename an access key."""
    try:
        result = client.rename_key(key_id, new_name)
        if result:
            print(f"Renamed key {key_id} to: {new_name}")
        else:
            print(f"Failed to rename key: {key_id}")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_limit(client, key_id, mb):
    """Set or remove data limit for a key."""
    try:
        if mb == 0:
            result = client.delete_data_limit(key_id)
            if result:
                print(f"Removed limit for key {key_id}")
            else:
                print(f"Failed to remove limit for key: {key_id}")
                sys.exit(1)
        else:
            # Convert MB to bytes
            limit_bytes = int(mb * 1024 * 1024)
            result = client.add_data_limit(key_id, limit_bytes)
            if result:
                print(f"Set limit for key {key_id}: {mb} MB")
            else:
                print(f"Failed to set limit for key: {key_id}")
                sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Manage Outline VPN access keys",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list
    subparsers.add_parser("list", help="List all access keys")

    # show
    show_parser = subparsers.add_parser("show", help="Show full key details")
    show_parser.add_argument("key_id", type=int, help="Key ID to show")

    # add
    add_parser = subparsers.add_parser("add", help="Create a new access key")
    add_parser.add_argument("--name", "-n", help="Name for the new key")

    # delete
    del_parser = subparsers.add_parser("delete", help="Delete an access key")
    del_parser.add_argument("key_id", type=int, help="Key ID to delete")

    # rename
    rename_parser = subparsers.add_parser("rename", help="Rename an access key")
    rename_parser.add_argument("key_id", type=int, help="Key ID to rename")
    rename_parser.add_argument("new_name", help="New name for the key")

    # limit
    limit_parser = subparsers.add_parser("limit", help="Set data limit (0 to remove)")
    limit_parser.add_argument("key_id", type=int, help="Key ID")
    limit_parser.add_argument("mb", type=float, help="Limit in MB (0 to remove)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    client = get_client()

    if args.command == "list":
        cmd_list(client)
    elif args.command == "show":
        cmd_show(client, args.key_id)
    elif args.command == "add":
        cmd_add(client, args.name)
    elif args.command == "delete":
        cmd_delete(client, args.key_id)
    elif args.command == "rename":
        cmd_rename(client, args.key_id, args.new_name)
    elif args.command == "limit":
        cmd_limit(client, args.key_id, args.mb)


if __name__ == "__main__":
    main()
