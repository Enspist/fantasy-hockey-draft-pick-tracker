#!/usr/bin/env python3
"""
Fantasy Hockey Draft Pick Tracker — cross-platform launcher.

Works on Windows, Linux, and macOS.  Run with:
    python run.py   OR   python3 run.py

Pulls the latest code from main, then starts the Discord bot.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()

if sys.platform == "win32":
    VENV_PYTHON = SCRIPT_DIR / "venv" / "Scripts" / "python.exe"
else:
    VENV_PYTHON = SCRIPT_DIR / "venv" / "bin" / "python"

REQUIRED_FILES = [
    "config/token_key.pkl",
    "config/token.pkl",
    "config/db_creds.pkl",
    "config/bot_config.yaml",
]


def _check_prerequisites() -> None:
    if not VENV_PYTHON.exists():
        print("ERROR: Virtual environment not found.")
        print("       Run install.py (or install.sh / install.cmd) first.")
        sys.exit(1)

    missing = [f for f in REQUIRED_FILES if not (SCRIPT_DIR / f).exists()]
    if missing:
        print("ERROR: The following required config files are missing:")
        for f in missing:
            print(f"         • {f}")
        print("       Run the installer to complete setup.")
        sys.exit(1)


def main() -> None:
    print("=" * 60)
    print("  Fantasy Hockey Draft Pick Tracker — Starting")
    print("=" * 60)
    print()

    _check_prerequisites()

    print("  Starting bot (will pull latest from main on startup)…")
    print("  Press Ctrl+C to stop.\n")

    try:
        subprocess.run(
            [str(VENV_PYTHON), str(SCRIPT_DIR / "main.py")],
            cwd=str(SCRIPT_DIR),
        )
    except KeyboardInterrupt:
        print("\n  Stopped.")


if __name__ == "__main__":
    main()
