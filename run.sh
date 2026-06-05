#!/usr/bin/env bash
# ============================================================
#  Fantasy Hockey Draft Pick Tracker — Linux/macOS launcher
#  Usage:  bash run.sh
#
#  Starts the webhook auto-pull server in the background, then
#  starts the Discord bot in the foreground.  Both processes are
#  stopped cleanly when you press Ctrl+C or the bot exits.
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

# ── Trap Ctrl+C / EXIT so we clean up the webhook process ────
WEBHOOK_PID=""

cleanup() {
    echo ""
    echo "  Shutting down…"
    if [ -n "$WEBHOOK_PID" ] && kill -0 "$WEBHOOK_PID" 2>/dev/null; then
        kill "$WEBHOOK_PID"
        wait "$WEBHOOK_PID" 2>/dev/null || true
        echo "  ✓ Webhook server stopped."
    fi
    echo "  ✓ Done."
}
trap cleanup EXIT INT TERM

# ── Start the webhook server in the background ───────────────
echo "  Starting webhook server…"
"$PYTHON_BIN" "$SCRIPT_DIR/webhook_server.py" &
WEBHOOK_PID=$!
echo "  ✓ Webhook server running (PID $WEBHOOK_PID)"
echo ""

# ── Start the Discord bot in the foreground ──────────────────
echo "  Starting Fantasy Hockey bot…"
echo "  (Press Ctrl+C to stop both processes)"
echo ""
"$PYTHON_BIN" "$SCRIPT_DIR/main.py"
