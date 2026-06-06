@echo off
REM ============================================================
REM  Fantasy Hockey Draft Pick Tracker -- Windows launcher
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

for %%F in (.token.key .token.enc .db_creds.enc bot_config.ini) do (
    if not exist "%SCRIPT_DIR%%%F" (
        echo ERROR: Required config file '%%F' is missing.
        echo        Run install.cmd to complete setup.
        pause
        exit /b 1
    )
)

REM ── Start the bot (pulls latest from main on startup) ────────
echo   Starting Fantasy Hockey bot...
echo   (Press Ctrl+C or close this window to stop)
echo.
"%PYTHON_BIN%" "%SCRIPT_DIR%main.py"

echo.
echo   Bot has stopped.
pause
