@echo off
REM ============================================================
REM  Fantasy Draft Pick Tracker -- Windows launcher
REM  Usage:  Double-click run.cmd  OR  run from Command Prompt
REM
REM  Pulls the latest code from main, then starts the Discord bot.
REM ============================================================
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PYTHON_BIN=%SCRIPT_DIR%venv\Scripts\python.exe"

REM ── Sanity checks ────────────────────────────────────────────
if not exist "%PYTHON_BIN%" (
    echo ERROR: Virtual environment not found.
    echo        Run install.cmd first.
    pause
    exit /b 1
)

for %%F in (config\secret\token_key.pkl config\secret\token.pkl config\secret\db_creds.pkl config\bot_config.yaml) do (
    if not exist "%SCRIPT_DIR%%%F" (
        echo ERROR: Required config file '%%F' is missing.
        echo        Run install.cmd to complete setup.
        pause
        exit /b 1
    )
)

REM ── Start the bot ────────────────────────────────────────────
REM    Set NO_PULL=1 to skip the git pull on startup (useful for
REM    testing local changes that haven't been pushed yet).
REM    Example:  set NO_PULL=1 && run.cmd
echo   Starting Fantasy Draft bot...
echo   (Press Ctrl+C or close this window to stop)
echo.
"%PYTHON_BIN%" "%SCRIPT_DIR%main.py"

echo.
echo   Bot has stopped.
pause
