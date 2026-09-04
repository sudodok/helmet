@echo off
chcp 65001 > nul
title [DEMO MODE] ระบบตรวจจับหมวกกันน็อค + GPS Geofence WebApp
echo =========================================================================
echo  🎮 กำลังเปิดระบบจำลองสำหรับนำเสนอ (PC Demo + GPS Geofence WebApp)
echo =========================================================================
echo  1. เปิด WebApp Server (100%% Offline) ที่ http://localhost:5000
echo  2. เปิดหน้าต่างจำลอง PC Demo HUD + เสียงเตือน + กล้อง
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
echo  🚀 กำลังเริ่มโปรแกรมจำลอง PC Demo...
echo  ปุ่มควบคุมสำคัญ:
echo    [H] สลับ สวมหมวก / ถอดหมวก
echo    [W] บิดคันเร่ง (เพิ่มความเร็ว)
echo    [S] เหยียบเบรก (ลดความเร็ว)
echo    [Q] ปิดโปรแกรม
echo =========================================================================
echo.

:: 4. รัน PC Demo ในหน้าต่างหลัก
python pc_demo.py

:: 5. เมื่อปิด PC Demo ให้ปิด WebApp Server ด้วย
echo.
echo [INFO] ปิดระบบ PC Demo เรียบร้อย กำลังปิด WebApp Server...
taskkill /FI "WINDOWTITLE eq GPS Geofence Server*" /F > nul 2>&1
echo [INFO] ปิดระบบทั้งหมดสมบูรณ์
pause
