@echo off
REM ============================================================
REM  Fantasy Hockey Draft Pick Tracker -- Windows launcher
REM  Usage:  Double-click run.cmd  OR  run from Command Prompt
REM
REM  Starts the webhook server in a separate window, then starts
REM  the Discord bot in this window.  Close the bot window (or
REM  press Ctrl+C) to stop the bot; the webhook window must be
REM  closed separately.
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

for %%F in (.token.key .token.enc .db_creds.enc bot_config.ini) do (
    if not exist "%SCRIPT_DIR%%%F" (
        echo ERROR: Required config file '%%F' is missing.
        echo        Run install.cmd to complete setup.
        pause
        exit /b 1
    )
)

REM ── Start the webhook server in a separate window ────────────
echo   Starting webhook server in a new window...
start "Fantasy Hockey - Webhook Server" "%PYTHON_BIN%" "%SCRIPT_DIR%webhook_server.py"
echo   [OK] Webhook server window opened.
echo.

REM ── Start the Discord bot in this window ─────────────────────
echo   Starting Fantasy Hockey bot...
echo   (Press Ctrl+C or close this window to stop the bot)
echo.
"%PYTHON_BIN%" "%SCRIPT_DIR%main.py"

echo.
echo   Bot has stopped.
pause
