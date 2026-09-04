@echo off
chcp 65001 > nul
title [REAL] ระบบตรวจจับหมวกนิรภัยของจริง (Hardware Mode) + Geofence WebApp
cd /d "%~dp0"

echo =========================================================================
echo   ⚡  เปิดระบบตรวจจับของจริง (REAL HARDWARE MODE)
echo   1. สตาร์ท WebApp Server (http://localhost:5000)
echo   2. เปิดระบบตรวจจับหมวกนิรภัยกล้องจริง + GPS + รีเลย์ควบคุมรถ
echo =========================================================================
echo.

:: 1. เปิด WebApp Server ในหน้าต่างย่อ (Minimized)
echo [1/3] กำลังสตาร์ท WebApp Server...
start "Helmet Geofence Server" /min python webapp\server.py

:: 2. รอเซิร์ฟเวอร์เริ่มทำงาน 2 วินาที แล้วเปิดเบราว์เซอร์
timeout /t 2 /nobreak > nul
echo [2/3] เปิดหน้าเว็บ Geofence Monitor (http://localhost:5000)...
start http://localhost:5000

:: 3. เปิดโปรแกรมตรวจจับหมวกกล้องจริง (helmet_detection.py)
echo [3/3] กำลังเริ่มโปรแกรมตรวจจับกล้องจริง (helmet_detection.py)...
echo.
echo =========================================================================
echo   📹 ระบบจะเปิดกล้องเพื่อตรวจจับผู้ขับขี่จริง
echo   - [Q] : ออกจากโปรแกรม
echo   - [S] : บันทึกภาพถ่ายเองด้วยตนเอง
echo   - [R] : รีเซ็ตสถิติระบบ
echo =========================================================================
echo.

python helmet_detection.py

echo.
echo [INFO] ปิดระบบเรียบร้อยแล้ว กำลังปิด WebApp Server...
taskkill /f /fi "WINDOWTITLE eq Helmet Geofence Server*" > nul 2>&1
echo [DONE] ปิดระบบทั้งหมดเสร็จสมบูรณ์
pause
