#!/usr/bin/env python3
"""
Initial setup script for the Fantasy Hockey Draft Pick Tracker bot.

Run once before starting the bot for the first time:
    python setup.py

What it does
------------
1. Auto-detects a local PostgreSQL instance (localhost:5432, 5433).
   If none is found, asks for the server IP and port.
2. Prompts for the database name, master PostgreSQL username, and master
   password, then connects and:
     • Creates the database if it does not already exist.
     • Creates the 'FantasyBot' application user if it does not already exist.
     • Grants full privileges on the database to 'FantasyBot'.
3. Saves { host, port, dbname, user, password } to an encrypted .pkl file
   (.db_creds.enc) protected by the same Fernet key used for the token.
4. Prompts for the Discord bot token → encrypted as .token.enc / .token.key.
5. Prompts for guild ID, admin role, picks channel, webhook settings
   → plain-text bot_config.ini (editable by hand).

Secret files written (all chmod 600 on Linux):
    .token.key      Fernet encryption key (protects both .token.enc and .db_creds.enc)
    .token.enc      Encrypted Discord bot token
    .db_creds.enc   Encrypted pickle containing DB connection credentials
"""

import asyncio
import configparser
import getpass
import os
import pickle
import socket
import sys
from pathlib import Path

import asyncpg
from cryptography.fernet import Fernet

# ── File paths ─────────────────────────────────────────────────────────────────
CONFIG_FILE     = Path("bot_config.ini")
TOKEN_KEY_FILE  = Path(".token.key")
TOKEN_ENC_FILE  = Path(".token.enc")
DB_CREDS_FILE   = Path(".db_creds.enc")

# Credentials used by the bot at runtime (never changes)
BOT_DB_USER     = "FantasyBot"
BOT_DB_PASSWORD = "FaNtAsYb0T"

# Ports to probe when auto-detecting a local PostgreSQL instance
POSTGRES_PROBE_PORTS = [5432, 5433]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _prompt(label: str, secret: bool = False, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    prompt_str = f"{label}{suffix}: "
    while True:
        value = (getpass.getpass(prompt_str) if secret else input(prompt_str)).strip()
        if not value and default:
            return default
        if value:
            return value
        print("  ✗ This field cannot be empty.")


def _restrict(path: Path) -> None:
    """chmod 600 on POSIX so only the owner can read the file."""
    if os.name == "posix":
        path.chmod(0o600)


def _load_or_create_fernet_key() -> bytes:
    """Return the existing key if present, otherwise generate and persist one."""
    if TOKEN_KEY_FILE.exists():
        return TOKEN_KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    TOKEN_KEY_FILE.write_bytes(key)
    _restrict(TOKEN_KEY_FILE)
    print(f"  ✓ New Fernet key generated → {TOKEN_KEY_FILE}")
    return key


def _fernet(key: bytes) -> Fernet:
    return Fernet(key)


# ── PostgreSQL auto-detection ──────────────────────────────────────────────────

def _probe_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if a TCP connection to host:port succeeds within timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def detect_postgres() -> tuple[str, int] | None:
    """
    Try common local PostgreSQL ports.
    Returns (host, port) if found, None otherwise.
    """
    for port in POSTGRES_PROBE_PORTS:
        if _probe_port("localhost", port):
            return "localhost", port
    return None


def resolve_postgres_host() -> tuple[str, int]:
    """
    Auto-detect a local Postgres instance; fall back to manual entry.
    Returns (host, port).
    """
    print("  Scanning for a local PostgreSQL instance…")
    result = detect_postgres()
    if result:
        host, port = result
        print(f"  ✓ Found PostgreSQL at {host}:{port}")
        return host, port

    print("  ✗ No local PostgreSQL instance detected.")
    print("    Enter the connection details for your remote PostgreSQL server.")
    host = _prompt("  PostgreSQL host / IP")
    port = int(_prompt("  PostgreSQL port", default="5432"))
    return host, port


# ── Database provisioning ──────────────────────────────────────────────────────

async def _provision_database(
    host: str,
    port: int,
    dbname: str,
    master_user: str,
    master_password: str,
) -> None:
    """
    Connect as the master user and:
      1. Create the target database (if absent).
      2. Create the 'FantasyBot' role (if absent).
      3. Grant all privileges on the database to 'FantasyBot'.
      4. Grant schema-level privileges inside the database.
    """
    # ── Step 1: connect to the default 'postgres' maintenance database ────────
    print(f"  Connecting to PostgreSQL at {host}:{port} as '{master_user}'…")
    try:
        admin_conn = await asyncpg.connect(
            host=host, port=port,
            user=master_user, password=master_password,
            database="postgres",
        )
    except Exception as exc:
        print(f"\n  ✗ Connection failed: {exc}")
        sys.exit(1)

    try:
        # ── Step 2: create the target database if it doesn't exist ────────────
        exists = await admin_conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", dbname
        )
        if not exists:
            # CREATE DATABASE cannot run inside a transaction block
            await admin_conn.execute(f'CREATE DATABASE "{dbname}"')
            print(f"  ✓ Database '{dbname}' created.")
        else:
            print(f"  ✓ Database '{dbname}' already exists.")

        # ── Step 3: create the FantasyBot role if it doesn't exist ───────────
        role_exists = await admin_conn.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname = $1", BOT_DB_USER
        )
        if not role_exists:
            await admin_conn.execute(
                f"CREATE USER \"{BOT_DB_USER}\" WITH PASSWORD '{BOT_DB_PASSWORD}'"
            )
            print(f"  ✓ User '{BOT_DB_USER}' created.")
        else:
            # Ensure the password is correct even if the user already existed
            await admin_conn.execute(
                f"ALTER USER \"{BOT_DB_USER}\" WITH PASSWORD '{BOT_DB_PASSWORD}'"
            )
            print(f"  ✓ User '{BOT_DB_USER}' already exists — password confirmed.")

        # ── Step 4: grant database-level privileges ───────────────────────────
        await admin_conn.execute(
            f'GRANT ALL PRIVILEGES ON DATABASE "{dbname}" TO "{BOT_DB_USER}"'
        )
        print(f"  ✓ Database-level privileges granted to '{BOT_DB_USER}'.")

    finally:
        await admin_conn.close()

    # ── Step 5: grant schema-level privileges (must connect to the target DB) ─
    db_conn = await asyncpg.connect(
        host=host, port=port,
        user=master_user, password=master_password,
        database=dbname,
    )
    try:
        await db_conn.execute(
            f'GRANT ALL ON SCHEMA public TO "{BOT_DB_USER}"'
        )
        await db_conn.execute(
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
            f'GRANT ALL ON TABLES TO "{BOT_DB_USER}"'
        )
        await db_conn.execute(
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
            f'GRANT ALL ON SEQUENCES TO "{BOT_DB_USER}"'
        )
        print(f"  ✓ Schema-level privileges granted to '{BOT_DB_USER}'.")
    finally:
        await db_conn.close()


# ── Credential persistence ────────────────────────────────────────────────────

def _save_db_creds(key: bytes, host: str, port: int, dbname: str) -> None:
    """Pickle the bot's DB credentials and encrypt them with the Fernet key."""
    creds = {
        "host":     host,
        "port":     port,
        "dbname":   dbname,
        "user":     BOT_DB_USER,
        "password": BOT_DB_PASSWORD,
    }
    raw = pickle.dumps(creds)
    encrypted = _fernet(key).encrypt(raw)
    DB_CREDS_FILE.write_bytes(encrypted)
    _restrict(DB_CREDS_FILE)
    print(f"  ✓ DB credentials encrypted → {DB_CREDS_FILE}")


def _encrypt_token(key: bytes, token: str) -> None:
    ciphertext = _fernet(key).encrypt(token.encode())
    TOKEN_ENC_FILE.write_bytes(ciphertext)
    _restrict(TOKEN_ENC_FILE)
    print(f"  ✓ Token encrypted → {TOKEN_ENC_FILE}")


def _write_config(guild_id: str, admin_role: str, picks_channel: str) -> None:
    cfg = configparser.ConfigParser()
    cfg["bot"] = {
        "guild_id":      guild_id,
        "admin_role":    admin_role,
        "picks_channel": picks_channel,
    }
    with CONFIG_FILE.open("w") as fh:
        cfg.write(fh)
    print(f"  ✓ Config written → {CONFIG_FILE}  (edit this file to change settings later)")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  Fantasy Hockey Draft Pick Tracker — Initial Setup")
    print("=" * 60)
    print()

    # ── 1. PostgreSQL ──────────────────────────────────────────────
    print("── PostgreSQL ──────────────────────────────────────────────")
    host, port = resolve_postgres_host()
    dbname       = _prompt("  Database name", default="fantasy_hockey")
    master_user  = _prompt("  Master PostgreSQL username", default="postgres")
    master_pass  = _prompt("  Master PostgreSQL password", secret=True)
    print()

    print("── Provisioning database ───────────────────────────────────")
    asyncio.run(_provision_database(host, port, dbname, master_user, master_pass))
    print()

    # ── 2. Discord token ───────────────────────────────────────────
    print("── Discord bot token ───────────────────────────────────────")
    print("  Your token will be shown as you type so you can verify it.")
    print("  It will be encrypted immediately after you press Enter.")
    token = _prompt("  Discord bot token")
    print()

    # ── 3. Discord server / bot settings ──────────────────────────
    print("── Discord server settings ─────────────────────────────────")
    guild_id      = _prompt("  Guild (server) ID")
    admin_role    = _prompt("  Admin role name", default="Commissioner")
    picks_channel = _prompt("  Picks board channel ID")
    print()

    # ── 5. Persist everything ──────────────────────────────────────
    print("── Saving configuration ────────────────────────────────────")
    fernet_key = _load_or_create_fernet_key()
    _save_db_creds(fernet_key, host, port, dbname)
    _encrypt_token(fernet_key, token)
    _write_config(guild_id, admin_role, picks_channel)

    print()
    print("=" * 60)
    print("  Setup complete!  Start the bot with:  python main.py")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)
