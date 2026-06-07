"""
Loads and decrypts the bot's PostgreSQL credentials from config/db_creds.pkl.

db_creds.pkl is a pickled blob of Fernet-encrypted bytes. Decrypting with the
key in config/token_key.pkl yields a pickled dict:
    {
        "host":     str,   # e.g. "localhost"
        "port":     int,   # e.g. 5432
        "dbname":   str,   # e.g. "fantasy_hockey"
        "user":     str,   # always "FantasyBot"
        "password": str,   # always "FaNtAsYb0T"
    }
"""

import pickle

from cryptography.fernet import Fernet

from paths import TOKEN_KEY_FILE, DB_CREDS_FILE


def _require(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Required file '{path}' is missing. Run the installer / setup.py first."
        )
    return path


def load_db_credentials() -> dict:
    """Return the decrypted DB credentials dict."""
    key        = pickle.loads(_require(TOKEN_KEY_FILE).read_bytes())
    ciphertext = pickle.loads(_require(DB_CREDS_FILE).read_bytes())
    raw        = Fernet(key).decrypt(ciphertext)
    return pickle.loads(raw)  # noqa: S301 — our own encrypted output


def build_database_url() -> str:
    """Return a postgresql:// URL suitable for asyncpg."""
    c = load_db_credentials()
    return f"postgresql://{c['user']}:{c['password']}@{c['host']}:{c['port']}/{c['dbname']}"
