@echo off
chcp 65001 > nul
title GPS Geofence Monitor (Offline)
echo =========================================================================
echo  🛰️  กำลังเปิดระบบ GPS Geofence Monitor (100%% Offline)...
echo =========================================================================
echo.
cd /d "%~dp0"
python webapp\server.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] ไม่สามารถเปิดโปรแกรมได้ กรุณาติดตั้ง dependencies ด้วยคำสั่ง:
    echo pip install flask flask-socketio simple-websocket
    pause
)
