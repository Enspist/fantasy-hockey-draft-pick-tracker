#!/usr/bin/env python3
"""
Fantasy Hockey Draft Pick Tracker — cross-platform launcher.

Works on Windows, Linux, and macOS.  Run with:
    python run.py   OR   python3 run.py

What it does
------------
1. Verifies the virtual environment and required config files are present.
2. Starts webhook_server.py as a background subprocess.
3. Starts main.py (the Discord bot) in the foreground.
4. On exit (Ctrl+C or natural bot shutdown) terminates the webhook server.
"""

import signal
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent.resolve()

# Venv Python path is platform-specific
if sys.platform == "win32":
    VENV_PYTHON = SCRIPT_DIR / "venv" / "Scripts" / "python.exe"
else:
    VENV_PYTHON = SCRIPT_DIR / "venv" / "bin" / "python"

REQUIRED_FILES = [
    ".token.key",
    ".token.enc",
    ".db_creds.enc",
    "bot_config.ini",
]


def _check_prerequisites() -> None:
    """Abort with a clear message if anything is missing."""
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


def _launch_webhook() -> subprocess.Popen:
    """Start webhook_server.py as a detached background process."""
    proc = subprocess.Popen(
        [str(VENV_PYTHON), str(SCRIPT_DIR / "webhook_server.py")],
        cwd=str(SCRIPT_DIR),
    )
    print(f"  ✓ Webhook server started (PID {proc.pid})")
    return proc


def _stop_webhook(proc: subprocess.Popen) -> None:
    """Gracefully terminate the webhook server."""
    if proc.poll() is None:          # still running
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("  ✓ Webhook server stopped.")


def main() -> None:
    print("=" * 60)
    print("  Fantasy Hockey Draft Pick Tracker — Starting")
    print("=" * 60)
    print()

    _check_prerequisites()

    # ── Launch webhook server ──────────────────────────────────
    print("  Starting webhook server…")
    webhook_proc = _launch_webhook()
    print()

    # ── Register cleanup on signals ───────────────────────────
    def _on_signal(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _on_signal)
    if hasattr(signal, "SIGBREAK"):          # Windows Ctrl+Break
        signal.signal(signal.SIGBREAK, _on_signal)

    # ── Launch the bot (foreground) ────────────────────────────
    print("  Starting Fantasy Hockey bot…")
    print("  (Press Ctrl+C to stop both processes)\n")

    bot_proc = None
    try:
        bot_proc = subprocess.run(
            [str(VENV_PYTHON), str(SCRIPT_DIR / "main.py")],
            cwd=str(SCRIPT_DIR),
        )
    except KeyboardInterrupt:
        print("\n  Received shutdown signal…")
    finally:
        if bot_proc is None or (hasattr(bot_proc, "returncode") and bot_proc.returncode is None):
            pass  # already exited or never started properly
        print("  Shutting down webhook server…")
        _stop_webhook(webhook_proc)
        print()
        print("  All processes stopped.  Goodbye!")


if __name__ == "__main__":
    main()
