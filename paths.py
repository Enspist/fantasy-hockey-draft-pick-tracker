"""
Central definitions for all config and secret file locations.

Everything config-related lives in the ./config directory, with the
encrypted secret files tucked into a hidden ./config/secret subfolder:

  config/bot_config.yaml        — plain-text settings (editable by hand)
  config/secret/token_key.pkl   — Fernet encryption key            (secret)
  config/secret/token.pkl       — encrypted Discord bot token       (secret)
  config/secret/db_creds.pkl    — encrypted DB connection details   (secret)

Paths are anchored to the project root so they resolve correctly no
matter what the current working directory is.
"""

import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()

CONFIG_DIR = PROJECT_ROOT / "config"
SECRET_DIR = CONFIG_DIR / "secret"

CONFIG_FILE    = CONFIG_DIR / "bot_config.yaml"
TOKEN_KEY_FILE = SECRET_DIR / "token_key.pkl"
TOKEN_ENC_FILE = SECRET_DIR / "token.pkl"
DB_CREDS_FILE  = SECRET_DIR / "db_creds.pkl"


def ensure_secret_dir() -> None:
    """Create config/secret and mark it hidden (Windows: hidden attribute)."""
    SECRET_DIR.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        # Set the hidden attribute; ignore errors if it's already set.
        subprocess.run(["attrib", "+h", str(SECRET_DIR)], check=False,
                       capture_output=True)
