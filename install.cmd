@echo off
REM ============================================================
REM  Fantasy Hockey Draft Pick Tracker -- Windows installer
REM  Usage:  Double-click install.cmd  OR  run from Command Prompt
REM ============================================================
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "VENV_DIR=%SCRIPT_DIR%venv"
set "PYTHON_BIN=%VENV_DIR%\Scripts\python.exe"
set "PIP_BIN=%VENV_DIR%\Scripts\pip.exe"

echo ============================================================
echo   Fantasy Hockey Draft Pick Tracker -- Installer
echo ============================================================
echo.

REM ── 1. Locate Python 3.11+ ──────────────────────────────────
set "PYTHON_CMD="
for %%P in (python3.13 python3.12 python3.11 python3 python) do (
    if "!PYTHON_CMD!"=="" (
        where %%P >nul 2>&1
        if !errorlevel! == 0 (
            for /f "delims=" %%V in ('%%P -c "import sys; print(sys.version_info >= (3,11))" 2^>nul') do (
                if "%%V"=="True" set "PYTHON_CMD=%%P"
            )
        )
    )
)

if "%PYTHON_CMD%"=="" (
    echo ERROR: Python 3.11 or newer is required but was not found.
    echo        Download it from https://python.org and re-run this script.
    pause
    exit /b 1
)

for /f "delims=" %%V in ('%PYTHON_CMD% --version 2^>^&1') do echo   Using Python: %%V
echo.

REM ── 2. Create virtual environment ───────────────────────────
if not exist "%VENV_DIR%\" (
    echo   Creating virtual environment in .\venv ...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if !errorlevel! neq 0 (
        echo   ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo   [OK] Virtual environment created.
) else (
    echo   [OK] Virtual environment already exists -- skipping creation.
)
echo.

REM ── 3. Install / upgrade dependencies ───────────────────────
echo   Installing dependencies ...
"%PIP_BIN%" install --upgrade pip --quiet
"%PIP_BIN%" install -r "%SCRIPT_DIR%requirements.txt" --quiet
if !errorlevel! neq 0 (
    echo   ERROR: Dependency installation failed.
    pause
    exit /b 1
)
echo   [OK] Dependencies installed.
echo.

REM ── 4. Run the interactive setup wizard ─────────────────────
echo   Starting setup wizard ...
echo.
"%PYTHON_BIN%" "%SCRIPT_DIR%setup.py"

echo.
echo   Installation complete.  Run the bot with:  run.cmd
pause
