"""
Loads and decrypts the bot's PostgreSQL credentials from .db_creds.enc.

The file is an encrypted pickle produced by setup.py.  It contains:
    {
        "host":     str,   # e.g. "localhost"
        "port":     int,   # e.g. 5432
        "dbname":   str,   # e.g. "fantasy_hockey"
        "user":     str,   # always "FantasyBot"
        "password": str,   # always "FaNtAsYb0T"
    }

The same Fernet key that protects .token.enc is used here (.token.key).
"""

import pickle
from pathlib import Path

from cryptography.fernet import Fernet

_TOKEN_KEY_FILE = Path(".token.key")
_DB_CREDS_FILE  = Path(".db_creds.enc")


def _require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(
            f"Required file '{path}' is missing.  Run 'python setup.py' first."
        )
    return path


def load_db_credentials() -> dict:
    """Return the decrypted DB credentials dict."""
    key        = _require(_TOKEN_KEY_FILE).read_bytes()
    ciphertext = _require(_DB_CREDS_FILE).read_bytes()
    raw        = Fernet(key).decrypt(ciphertext)
    return pickle.loads(raw)  # noqa: S301 — file is our own encrypted output


def build_database_url() -> str:
    """Return a postgresql:// URL suitable for asyncpg."""
    c = load_db_credentials()
    return f"postgresql://{c['user']}:{c['password']}@{c['host']}:{c['port']}/{c['dbname']}"
