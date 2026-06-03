"""
Runtime configuration loader.

Reads settings from three sources (all created by setup.py):
  bot_config.ini  — guild ID, admin role, channel, webhook settings  (plain text)
  .token.key      — Fernet encryption key                            (chmod 600)
  .token.enc      — encrypted Discord token                          (chmod 600)
  .db_url         — PostgreSQL connection string                     (chmod 600)
"""

import configparser
from pathlib import Path

from cryptography.fernet import Fernet

_CONFIG_FILE    = Path("bot_config.ini")
_TOKEN_KEY_FILE = Path(".token.key")
_TOKEN_ENC_FILE = Path(".token.enc")
_DB_URL_FILE    = Path(".db_url")


def _require_file(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(
            f"Required file '{path}' not found. Run 'python setup.py' first."
        )
    return path


def _load_ini() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(_require_file(_CONFIG_FILE))
    return cfg


def _decrypt_token() -> str:
    key = _require_file(_TOKEN_KEY_FILE).read_bytes()
    ciphertext = _require_file(_TOKEN_ENC_FILE).read_bytes()
    return Fernet(key).decrypt(ciphertext).decode()


def _load_db_url() -> str:
    return _require_file(_DB_URL_FILE).read_text().strip()


# ── Exported values ────────────────────────────────────────────────────────────

_ini = _load_ini()

DISCORD_TOKEN: str  = _decrypt_token()
DATABASE_URL: str   = _load_db_url()

GUILD_ID: int       = int(_ini["bot"]["guild_id"])
ADMIN_ROLE: str     = _ini["bot"]["admin_role"]
PICKS_CHANNEL: int  = int(_ini["bot"]["picks_channel"])

WEBHOOK_SECRET: str = _ini["webhook"]["webhook_secret"]
WEBHOOK_PORT: int   = int(_ini["webhook"].get("port", "5000"))
