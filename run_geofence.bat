@echo off
title GPS Geofence Monitor (Offline)
cd /d "%~dp0"
echo =========================================================================
echo   Starting GPS Geofence Monitor (100%% Offline)...
echo   URL: http://localhost:5000
echo =========================================================================
echo.
python webapp\server.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to start. Please run: pip install flask flask-socketio simple-websocket
    pause
)
