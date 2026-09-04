@echo off
chcp 65001 > nul
title [REAL MODE] ระบบตรวจจับหมวกกันน็อคจริง + GPS Geofence WebApp
echo =========================================================================
echo  ⚡ กำลังเปิดระบบฮาร์ดแวร์จริง (Real Hardware + GPS Geofence WebApp)
echo =========================================================================
echo  1. เปิด WebApp Server (100%% Offline) ที่ http://localhost:5000
echo  2. เปิดกล้องตรวจจับหมวกกันน็อคจริง (YOLO/Camera + GPS + Controller)
echo =========================================================================
echo.

cd /d "%~dp0"

:: 1. รัน WebApp Server ในหน้าต่างเบื้องหลัง
echo [1/3] เริ่มการทำงานของ WebApp Server...
start "GPS Geofence Server (Offline)" /min cmd /c "python webapp\server.py"

:: 2. รอ 2 วินาทีให้ Server พร้อม
echo [2/3] กำลังเตรียมความพร้อมระบบสื่อสารภายใน...
timeout /t 2 > nul

:: 3. เปิดเว็บเบราว์เซอร์ดู Dashboard
echo [3/3] เปิด Web Dashboard (http://localhost:5000)...
start http://localhost:5000

echo.
echo =========================================================================
echo  🚀 กำลังเริ่มโปรแกรมตรวจจับจริง (helmet_detection.py)...
echo  ปุ่มควบคุม:
echo    [S] บันทึกภาพถ่ายและพิกัดด้วยตนเอง
echo    [R] รีเซ็ตสถิติระบบ
echo    [Q] ปิดระบบ
echo =========================================================================
echo.

:: 4. รันระบบจริงในหน้าต่างหลัก
python helmet_detection.py

:: 5. เมื่อปิดระบบให้ปิด WebApp Server ด้วย
echo.
echo [INFO] ปิดระบบตรวจจับจริงเรียบร้อย กำลังปิด WebApp Server...
taskkill /FI "WINDOWTITLE eq GPS Geofence Server*" /F > nul 2>&1
echo [INFO] ปิดระบบทั้งหมดสมบูรณ์
pause
