#!/usr/bin/env python3
"""Minimal CLI for managing Outline VPN access keys."""

import argparse
import configparser
import os
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".outline"
CONFIG_FILE = CONFIG_DIR / "config.ini"
OLD_ENV_FILE = Path(__file__).parent / ".env"

EXAMPLES = """Examples:
  outline_cli.py list
  outline_cli.py add --name laptop
  outline_cli.py add laptop
  outline_cli.py show 1
  outline_cli.py rename 1 "Work iPhone"
  outline_cli.py limit 1 1024
  outline_cli.py limit 1 0
  outline_cli.py profile add home
  outline_cli.py --profile home list
"""


class OutlineArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help(sys.stderr)
        self.exit(2, f"\nError: {message}\n")


def check_dependencies():
    """Check and import required packages."""
    try:
        from outline_vpn.outline_vpn import OutlineVPN
        return OutlineVPN
    except ImportError:
        print("Missing dependencies. Install with:")
        print("  pip install outline-vpn-api")
        sys.exit(1)


def ensure_config_dir():
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def migrate_from_env():
    """Migrate credentials from old .env file to new config.ini."""
    if not OLD_ENV_FILE.exists() or CONFIG_FILE.exists():
        return False

    try:
        from dotenv import load_dotenv
        load_dotenv(OLD_ENV_FILE)
        api_url = os.getenv("OUTLINE_API_URL")
        cert_sha256 = os.getenv("OUTLINE_CERT_SHA256")

        if api_url and cert_sha256:
            ensure_config_dir()
            save_profile("default", api_url, cert_sha256)
            print(f"Migrated credentials from .env to 'default' profile")
            print(f"Config now stored in: {CONFIG_FILE}")
            print()
            return True
    except ImportError:
        pass
    return False


def get_config():
    """Get configparser object for config file."""
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
    return config


def load_profile(profile="default"):
    """Load credentials for a specific profile."""
    config = get_config()
    if profile not in config.sections():
        return None, None
    return config.get(profile, "api_url", fallback=None), config.get(profile, "cert_sha256", fallback=None)


def save_profile(profile, api_url, cert_sha256):
    """Save credentials for a profile."""
    ensure_config_dir()
    config = get_config()
    if profile not in config.sections():
        config.add_section(profile)
    config.set(profile, "api_url", api_url)
    config.set(profile, "cert_sha256", cert_sha256)
    with open(CONFIG_FILE, "w") as f:
        config.write(f)


def list_profiles():
    """Return list of all profile names."""
    config = get_config()
    return config.sections()


def remove_profile(profile):
    """Remove a profile from config."""
    config = get_config()
    if profile not in config.sections():
        return False
    config.remove_section(profile)
    with open(CONFIG_FILE, "w") as f:
        config.write(f)
    return True


def setup_profile(profile):
    """Prompt user for credentials and save to profile."""
    print(f"Setup profile '{profile}': Enter your Outline server credentials")
    print()
    api_url = input("API URL (e.g., https://x.x.x.x:port/prefix): ").strip()
    cert_sha256 = input("Certificate SHA256: ").strip()

    if not api_url or not cert_sha256:
        print("Error: Both values are required")
        sys.exit(1)

    save_profile(profile, api_url, cert_sha256)
    print(f"Profile '{profile}' saved to {CONFIG_FILE}")
    return api_url, cert_sha256


def get_client(profile="default"):
    """Get configured Outline client for a profile."""
    OutlineVPN = check_dependencies()

    # Try migration from old .env
    migrate_from_env()

    api_url, cert_sha256 = load_profile(profile)

    if not api_url or not cert_sha256:
        profiles = list_profiles()
        if profiles:
            print(f"Error: Profile '{profile}' not found")
            print(f"Available profiles: {', '.join(profiles)}")
            sys.exit(1)
        else:
            print("No profiles configured.")
            api_url, cert_sha256 = setup_profile(profile)

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
        key = client.create_key(name=name) if name else client.create_key()
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


def cmd_profile_add(name):
    """Add a new profile."""
    profiles = list_profiles()
    if name in profiles:
        print(f"Profile '{name}' already exists. Use 'profile show {name}' to view it.")
        sys.exit(1)
    setup_profile(name)


def cmd_profile_list():
    """List all profiles."""
    profiles = list_profiles()
    if not profiles:
        print("No profiles configured.")
        print("Run: outline_cli.py profile add <name>")
        return

    print(f"{'Profile':<20} API URL")
    print("-" * 60)
    for profile in profiles:
        api_url, _ = load_profile(profile)
        # Truncate long URLs
        if len(api_url) > 38:
            api_url = api_url[:35] + "..."
        print(f"{profile:<20} {api_url}")


def cmd_profile_remove(name):
    """Remove a profile."""
    if name not in list_profiles():
        print(f"Profile '{name}' not found")
        sys.exit(1)

    confirm = input(f"Delete profile '{name}'? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled")
        return

    if remove_profile(name):
        print(f"Removed profile: {name}")
    else:
        print(f"Failed to remove profile: {name}")
        sys.exit(1)


def cmd_profile_show(name):
    """Show profile details."""
    if name not in list_profiles():
        print(f"Profile '{name}' not found")
        sys.exit(1)

    api_url, cert_sha256 = load_profile(name)
    # Mask most of the cert for security
    masked_cert = cert_sha256[:8] + "..." + cert_sha256[-8:] if len(cert_sha256) > 20 else cert_sha256

    print(f"Profile:     {name}")
    print(f"API URL:     {api_url}")
    print(f"Cert SHA256: {masked_cert}")


def main():
    parser = OutlineArgumentParser(
        description="Manage Outline VPN access keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXAMPLES
    )
    parser.add_argument(
        "--profile", "-p",
        default="default",
        help="Profile name to use (default: 'default')"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list
    subparsers.add_parser("list", help="List all access keys")

    # show
    show_parser = subparsers.add_parser("show", help="Show full key details")
    show_parser.add_argument("key_id", type=int, help="Key ID to show")

    # add
    add_parser = subparsers.add_parser("add", help="Create a new access key")
    add_parser.add_argument("name", nargs="?", help="Name for the new key (positional)")
    add_parser.add_argument("--name", "-n", dest="name", help="Name for the new key (flag)")

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

    # profile management
    profile_parser = subparsers.add_parser("profile", help="Manage server profiles")
    profile_subparsers = profile_parser.add_subparsers(dest="profile_cmd", help="Profile command")

    profile_add = profile_subparsers.add_parser("add", help="Add a new profile")
    profile_add.add_argument("name", help="Profile name")

    profile_subparsers.add_parser("list", help="List all profiles")

    profile_remove = profile_subparsers.add_parser("remove", help="Remove a profile")
    profile_remove.add_argument("name", help="Profile name to remove")

    profile_show = profile_subparsers.add_parser("show", help="Show profile details")
    profile_show.add_argument("name", help="Profile name to show")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Handle profile commands (no client needed)
    if args.command == "profile":
        if not args.profile_cmd:
            profile_parser.print_help()
            sys.exit(1)
        if args.profile_cmd == "add":
            cmd_profile_add(args.name)
        elif args.profile_cmd == "list":
            cmd_profile_list()
        elif args.profile_cmd == "remove":
            cmd_profile_remove(args.name)
        elif args.profile_cmd == "show":
            cmd_profile_show(args.name)
        return

    # Commands that require a client
    client = get_client(args.profile)

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
