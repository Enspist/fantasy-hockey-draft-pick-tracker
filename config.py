"""
Runtime configuration loader.

Sources (all created by setup.py — never committed to git):
  bot_config.ini   — guild ID, admin role name, channel  (plain text, editable)
  .token.key       — Fernet encryption key shared by token + DB creds  (chmod 600)
  .token.enc       — encrypted Discord bot token                        (chmod 600)
  .db_creds.enc    — encrypted pickle: DB host/port/name/user/password  (chmod 600)
"""

import configparser
from pathlib import Path

from cryptography.fernet import Fernet

_CONFIG_FILE    = Path("bot_config.ini")
_TOKEN_KEY_FILE = Path(".token.key")
_TOKEN_ENC_FILE = Path(".token.enc")


def _require_file(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(
            f"Required file '{path}' not found.  Run 'python setup.py' first."
        )
    return path


def _load_ini() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(_require_file(_CONFIG_FILE))
    return cfg


def _decrypt_token() -> str:
    key        = _require_file(_TOKEN_KEY_FILE).read_bytes()
    ciphertext = _require_file(_TOKEN_ENC_FILE).read_bytes()
    return Fernet(key).decrypt(ciphertext).decode()


# ── Exported values ────────────────────────────────────────────────────────────

_ini = _load_ini()

DISCORD_TOKEN: str  = _decrypt_token()

# DATABASE_URL is built lazily from the encrypted .db_creds.enc file.
# Import it from database.credentials to avoid a circular import at startup.
from database.credentials import build_database_url  # noqa: E402
DATABASE_URL: str   = build_database_url()

GUILD_ID: int       = int(_ini["bot"]["guild_id"])
ADMIN_ROLE: str     = _ini["bot"]["admin_role"]
PICKS_CHANNEL: int  = int(_ini["bot"]["picks_channel"])
LOG_KEEP: int       = int(_ini["bot"].get("log_keep", "5"))

# How long (seconds) before ephemeral admin-command replies auto-delete
REPLY_DELETE_AFTER: int = 300

