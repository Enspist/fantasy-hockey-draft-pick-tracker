#!/usr/bin/env python3
"""
Fantasy Draft Pick Tracker — cross-platform installer.

Works on Windows, Linux, and macOS.  Run with any Python 3.11+:
    python install.py   OR   python3 install.py

Steps
-----
1. Locates a Python 3.11+ interpreter on PATH.
2. Creates a virtual environment in ./venv (skips if it already exists).
3. Installs all packages listed in requirements.txt into the venv.
4. Launches setup.py (the interactive configuration wizard) using the
   venv's Python so all imports resolve correctly.
"""

import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
VENV_DIR   = SCRIPT_DIR / "venv"

# Platform-specific paths inside the venv
if sys.platform == "win32":
    VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
    VENV_PIP    = VENV_DIR / "Scripts" / "pip.exe"
else:
    VENV_PYTHON = VENV_DIR / "bin" / "python"
    VENV_PIP    = VENV_DIR / "bin" / "pip"


def _banner(text: str) -> None:
    print(f"\n── {text} {'─' * max(0, 54 - len(text))}")


def _run(*args, **kwargs) -> None:
    """Run a command, raising SystemExit on failure."""
    result = subprocess.run(args, **kwargs)
    if result.returncode != 0:
        print(f"\nERROR: Command failed: {' '.join(str(a) for a in args)}")
        sys.exit(result.returncode)


def find_python311() -> str:
    """
    Return the path to a Python 3.11+ executable, or exit with an error.
    Prefers the interpreter that launched this script if it is new enough.
    """
    if sys.version_info >= (3, 11):
        return sys.executable

    candidates = [
        "python3.13", "python3.12", "python3.11",
        "python3", "python",
    ]
    for name in candidates:
        path = shutil.which(name)
        if not path:
            continue
        try:
            result = subprocess.run(
                [path, "-c", "import sys; print(sys.version_info >= (3,11))"],
                capture_output=True, text=True,
            )
            if result.stdout.strip() == "True":
                return path
        except OSError:
            continue

    print("ERROR: Python 3.11 or newer is required but was not found.")
    print("       Install it from https://python.org and re-run this script.")
    sys.exit(1)


def create_venv(python_exe: str) -> None:
    if VENV_DIR.exists():
        print(f"  ✓ Virtual environment already exists — skipping creation.")
        return
    print(f"  Creating virtual environment in ./venv …")
    _run(python_exe, "-m", "venv", str(VENV_DIR))
    print(f"  ✓ Virtual environment created.")


def install_dependencies() -> None:
    req = SCRIPT_DIR / "requirements.txt"
    if not req.exists():
        print("  WARNING: requirements.txt not found — skipping dependency install.")
        return
    print("  Installing dependencies …")
    _run(str(VENV_PIP), "install", "--upgrade", "pip", "--quiet")
    _run(str(VENV_PIP), "install", "-r", str(req), "--quiet")
    print("  ✓ Dependencies installed.")


def run_setup_wizard() -> None:
    setup = SCRIPT_DIR / "setup.py"
    if not setup.exists():
        print("ERROR: setup.py not found.")
        sys.exit(1)
    print("  Launching setup wizard …\n")
    # Replace this process so the wizard runs interactively in the foreground
    subprocess.run([str(VENV_PYTHON), str(setup)])


def main() -> None:
    print("=" * 60)
    print("  Fantasy Draft Pick Tracker — Installer")
    print("=" * 60)

    _banner("Locating Python 3.11+")
    python_exe = find_python311()
    result = subprocess.run(
        [python_exe, "--version"], capture_output=True, text=True
    )
    print(f"  Using: {result.stdout.strip() or result.stderr.strip()}")

    _banner("Virtual environment")
    create_venv(python_exe)

    _banner("Dependencies")
    install_dependencies()

    _banner("Setup wizard")
    run_setup_wizard()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled.")
        sys.exit(1)
