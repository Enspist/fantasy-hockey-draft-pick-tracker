#!/usr/bin/env bash
# ============================================================
#  Fantasy Hockey Draft Pick Tracker — Linux/macOS installer
#  Usage:  bash install.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

echo "============================================================"
echo "  Fantasy Hockey Draft Pick Tracker — Installer"
echo "============================================================"
echo ""

# ── 1. Locate a suitable Python 3.11+ interpreter ────────────
find_python() {
    for cmd in python3.13 python3.12 python3.11 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            ver=$("$cmd" -c "import sys; print(sys.version_info >= (3,11))" 2>/dev/null)
            if [ "$ver" = "True" ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_CMD=$(find_python || true)
if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Python 3.11 or newer is required but was not found."
    echo "       Install it from https://python.org and re-run this script."
    exit 1
fi
echo "  Using Python: $($PYTHON_CMD --version)"
echo ""

# ── 2. Create virtual environment ────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "  Creating virtual environment in ./venv …"
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    echo "  ✓ Virtual environment created."
else
    echo "  ✓ Virtual environment already exists — skipping creation."
fi
echo ""

# ── 3. Install / upgrade dependencies ────────────────────────
echo "  Installing dependencies …"
"$PIP_BIN" install --upgrade pip --quiet
"$PIP_BIN" install -r "$SCRIPT_DIR/requirements.txt" --quiet
echo "  ✓ Dependencies installed."
echo ""

# ── 4. Run the interactive setup wizard ──────────────────────
echo "  Starting setup wizard …"
echo ""
"$PYTHON_BIN" "$SCRIPT_DIR/setup.py"
