@echo off
title Helmet Detection System - Real Mode (Hardware)
cd /d "%~dp0"

echo =========================================================================
echo   HELMET DETECTION SYSTEM - REAL HARDWARE MODE
echo   1. Starting WebApp Server (http://localhost:5000)...
echo   2. Opening Real Helmet Detection (Camera + GPS)...
echo =========================================================================
echo.

REM 1. Start WebApp Server in minimized window
echo [1/3] Starting WebApp Server...
start "Helmet Geofence Server" /min python webapp\server.py

REM 2. Wait 2 seconds and open browser
ping 127.0.0.1 -n 3 > nul
echo [2/3] Opening WebApp (http://localhost:5000)...
start http://localhost:5000

REM 3. Run Real Helmet Detection
echo [3/3] Starting Helmet Detection System...
echo.
echo =========================================================================
echo   - [Q] : Quit
echo   - [S] : Save snapshot manually
echo   - [R] : Reset statistics
echo =========================================================================
echo.

python helmet_detection.py

echo.
echo [INFO] Stopping WebApp Server...
taskkill /f /fi "WINDOWTITLE eq Helmet Geofence Server*" > nul 2>&1
echo [DONE] Finished.
pause
