@echo off
REM This script is for Windows to run the Python script in the background.
REM It uses pythonw.exe to suppress the console window.

REM Change directory to the script's location
cd /d "%~dp0"

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Check if the process is already running to prevent multiple instances
tasklist /FI "WINDOWTITLE eq Payout Hunter" | find /I "pythonw.exe"
if %errorlevel% equ 0 (
    echo Payout Hunter is already running. Exiting.
    exit /b 0
)

REM Start the script in the background using pythonw.exe
start "Payout Hunter" venv\Scripts\pythonw.exe payout_hunter.py

REM Deactivate the virtual environment (not strictly necessary but good practice)
call venv\Scripts\deactivate.bat
