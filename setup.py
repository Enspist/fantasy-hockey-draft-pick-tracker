#!/usr/bin/env python3
"""
Initial setup script for the Fantasy Hockey Draft Pick Tracker bot.

Run once before starting the bot for the first time:
    python setup.py

What it does
------------
1. Prompts for guild ID, admin role name, picks channel ID  → bot_config.ini
2. Prompts for GitHub webhook secret                        → bot_config.ini
3. Prompts for the Discord bot token                        → encrypted files
   - .token.key  (Fernet key  — keep this safe, chmod 600)
   - .token.enc  (ciphertext  — useless without the key)
4. Prompts for the PostgreSQL DATABASE_URL                  → .db_url  (chmod 600)

bot_config.ini is plain text and can be edited by hand at any time.
To change the token later just run this script again.
"""

import configparser
import getpass
import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet

CONFIG_FILE = Path("bot_config.ini")
TOKEN_KEY_FILE = Path(".token.key")
TOKEN_ENC_FILE = Path(".token.enc")
DB_URL_FILE = Path(".db_url")


def _prompt(label: str, secret: bool = False, default: str = "") -> str:
    """Prompt the user for input, optionally hiding it."""
    suffix = f" [{default}]" if default else ""
    prompt_str = f"{label}{suffix}: "
    while True:
        value = (getpass.getpass(prompt_str) if secret else input(prompt_str)).strip()
        if not value and default:
            return default
        if value:
            return value
        print("  ✗ This field cannot be empty.")


def _encrypt_token(token: str) -> None:
    """Generate a Fernet key, encrypt the token, and write both files."""
    key = Fernet.generate_key()
    fernet = Fernet(key)
    ciphertext = fernet.encrypt(token.encode())

    TOKEN_KEY_FILE.write_bytes(key)
    TOKEN_ENC_FILE.write_bytes(ciphertext)

    # Restrict permissions on Unix systems
    if os.name == "posix":
        TOKEN_KEY_FILE.chmod(0o600)
        TOKEN_ENC_FILE.chmod(0o600)

    print(f"  ✓ Token encrypted → {TOKEN_ENC_FILE}  (key → {TOKEN_KEY_FILE})")


def _write_config(guild_id: str, admin_role: str, picks_channel: str,
                  webhook_secret: str, webhook_port: str) -> None:
    config = configparser.ConfigParser()
    config["bot"] = {
        "guild_id": guild_id,
        "admin_role": admin_role,
        "picks_channel": picks_channel,
    }
    config["webhook"] = {
        "webhook_secret": webhook_secret,
        "port": webhook_port,
    }
    with CONFIG_FILE.open("w") as fh:
        config.write(fh)
    print(f"  ✓ Config written  → {CONFIG_FILE}  (edit this file to change settings later)")


def _write_db_url(db_url: str) -> None:
    DB_URL_FILE.write_text(db_url + "\n")
    if os.name == "posix":
        DB_URL_FILE.chmod(0o600)
    print(f"  ✓ Database URL saved → {DB_URL_FILE}")


def main() -> None:
    print("=" * 60)
    print(" Fantasy Hockey Draft Pick Tracker — Initial Setup")
    print("=" * 60)
    print()

    # ── 1. Bot / server settings ──────────────────────────────────
    print("── Discord server settings ─────────────────────────────────")
    guild_id = _prompt("Guild (server) ID")
    admin_role = _prompt("Admin role name (can use bot commands)", default="Commissioner")
    picks_channel = _prompt("Picks board channel ID")
    print()

    # ── 2. Webhook ────────────────────────────────────────────────
    print("── GitHub webhook settings ─────────────────────────────────")
    print("  (Set this same secret in GitHub → repo → Settings → Webhooks)")
    webhook_secret = _prompt("Webhook secret")
    webhook_port = _prompt("Webhook listener port", default="5000")
    print()

    # ── 3. Discord token (encrypted) ─────────────────────────────
    print("── Discord bot token (will be encrypted) ───────────────────")
    token = _prompt("Discord bot token", secret=True)
    print()

    # ── 4. Database URL ───────────────────────────────────────────
    print("── PostgreSQL connection ────────────────────────────────────")
    db_url = _prompt(
        "Database URL",
        secret=True,
        default="postgresql://user:password@localhost:5432/fantasy_hockey",
    )
    print()

    # ── Write everything ──────────────────────────────────────────
    print("── Saving configuration ────────────────────────────────────")
    _write_config(guild_id, admin_role, picks_channel, webhook_secret, webhook_port)
    _encrypt_token(token)
    _write_db_url(db_url)

    print()
    print("=" * 60)
    print(" Setup complete!  Start the bot with:  python main.py")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)
