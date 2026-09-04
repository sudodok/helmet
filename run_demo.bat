@echo off
title Helmet Detection System - Demo Mode
cd /d "%~dp0"

echo =========================================================================
echo   HELMET DETECTION SYSTEM - DEMO MODE
echo   1. Starting WebApp Server (http://localhost:5000)...
echo   2. Opening PC Demo Simulator...
echo =========================================================================
echo.

REM 1. Start WebApp Server in minimized window
echo [1/3] Starting WebApp Server...
start "Helmet Geofence Server" /min python webapp\server.py

REM 2. Wait 2 seconds and open browser
ping 127.0.0.1 -n 3 > nul
echo [2/3] Opening WebApp (http://localhost:5000)...
start http://localhost:5000

REM 3. Run PC Demo Simulator in current window
echo [3/3] Starting PC Demo Simulator...
echo.
echo =========================================================================
echo   CONTROLS:
echo   - [H] : Toggle Helmet ON / OFF
echo   - [T] : Throttle Up (+5 km/h)
echo   - [B] : Brake Down (-10 km/h)
echo   - [M] : Toggle Camera / Synthetic mode
echo   - [Q] : Quit
echo =========================================================================
echo.

python pc_demo.py

echo.
echo [INFO] Stopping WebApp Server...
taskkill /f /fi "WINDOWTITLE eq Helmet Geofence Server*" > nul 2>&1
echo [DONE] Finished.
pause
