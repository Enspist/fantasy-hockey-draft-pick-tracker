"""
Runtime configuration loader.

Sources (all created by setup.py, all under ./config — never committed):
  config/bot_config.yaml   — guild ID, roles, channel, log_keep  (plain YAML, editable)
  config/token_key.pkl     — pickled Fernet key                  (secret)
  config/token.pkl         — pickled encrypted Discord token      (secret)
  config/db_creds.pkl      — pickled encrypted DB credentials     (secret)
"""

import pickle

import yaml
from cryptography.fernet import Fernet

from paths import CONFIG_FILE, TOKEN_KEY_FILE, TOKEN_ENC_FILE


def _require_file(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Required file '{path}' not found. Run the installer / setup.py first."
        )
    return path


def _load_yaml() -> dict:
    with _require_file(CONFIG_FILE).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _decrypt_token() -> str:
    key        = pickle.loads(_require_file(TOKEN_KEY_FILE).read_bytes())
    ciphertext = pickle.loads(_require_file(TOKEN_ENC_FILE).read_bytes())
    return Fernet(key).decrypt(ciphertext).decode()


# ── Exported values ────────────────────────────────────────────────────────────

_cfg = _load_yaml()
_bot = _cfg.get("bot", {})

DISCORD_TOKEN: str  = _decrypt_token()

# DATABASE_URL is built from the encrypted db_creds.pkl file.
from database.credentials import build_database_url  # noqa: E402
DATABASE_URL: str   = build_database_url()

GUILD_ID: int       = int(_bot["guild_id"])
ADMIN_ROLE: str     = str(_bot["admin_role"])
PICKS_CHANNEL: int  = int(_bot["picks_channel"])
LOG_KEEP: int       = int(_bot.get("log_keep", 5))

# Optional role that can run bot-management commands (/bot restart) only.
BOT_ADMIN_ROLE: str = str(_bot.get("bot_admin_role") or "").strip()

# How long (seconds) before ephemeral admin-command replies auto-delete.
REPLY_DELETE_AFTER: int = 300
