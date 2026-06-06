#!/usr/bin/env bash
# ============================================================
#  Fantasy Hockey Draft Pick Tracker — Linux/macOS launcher
#  Usage:  bash run.sh
#
#  Pulls the latest code from main, then starts the Discord bot.
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"

# ── Sanity checks ─────────────────────────────────────────────
if [ ! -f "$PYTHON_BIN" ]; then
    echo "ERROR: Virtual environment not found."
    echo "       Run install.sh first."
    exit 1
fi

for secret in .token.key .token.enc .db_creds.enc bot_config.ini; do
    if [ ! -f "$SCRIPT_DIR/$secret" ]; then
        echo "ERROR: Required config file '$secret' is missing."
        echo "       Run install.sh to complete setup."
        exit 1
    fi
done

# ── Start the bot (pulls latest from main on startup) ─────────
echo "  Starting Fantasy Hockey bot..."
echo "  (Press Ctrl+C to stop)"
echo ""
"$PYTHON_BIN" "$SCRIPT_DIR/main.py"
