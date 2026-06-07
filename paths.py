"""
Central definitions for all config and secret file locations.

Everything config-related lives in the ./config directory:

  config/bot_config.yaml   — plain-text settings (editable by hand)
  config/token_key.pkl     — Fernet encryption key            (secret)
  config/token.pkl         — encrypted Discord bot token       (secret)
  config/db_creds.pkl      — encrypted DB connection details   (secret)

Paths are anchored to the project root so they resolve correctly no
matter what the current working directory is.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()

CONFIG_DIR = PROJECT_ROOT / "config"

CONFIG_FILE    = CONFIG_DIR / "bot_config.yaml"
TOKEN_KEY_FILE = CONFIG_DIR / "token_key.pkl"
TOKEN_ENC_FILE = CONFIG_DIR / "token.pkl"
DB_CREDS_FILE  = CONFIG_DIR / "db_creds.pkl"
