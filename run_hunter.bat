@echo off
REM This script is for Windows to run the Python script in the background.

REM Change directory to the script's location
cd /d "%~dp0"

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM --- 1. Start the Payout Hunter Script ---
REM Check if the hunter process is already running
tasklist /FI "WINDOWTITLE eq Payout Hunter" | find /I "pythonw.exe"
if %errorlevel% neq 0 (
    echo Starting Payout Hunter...
    REM Start the script in the background using pythonw.exe
    start "Payout Hunter" venv\Scripts\pythonw.exe payout_hunter.py
) else (
    echo Payout Hunter is already running.
)

REM --- 2. Start the Monitoring Dashboard ---
REM Check if the dashboard process is already running (Flask runs on port 5000 by default)
netstat -ano | findstr :5000 | findstr LISTENING
if %errorlevel% neq 0 (
    echo Starting Dashboard Server on http://localhost:5000...
    REM Start the Flask server in the background using start /B
    start /B venv\Scripts\python.exe dashboard.py
) else (
    echo Dashboard is already running on port 5000.
)

REM Deactivate the virtual environment (not strictly necessary but good practice)
call venv\Scripts\deactivate.bat
