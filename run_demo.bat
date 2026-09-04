@echo off
chcp 65001 > nul
title [DEMO] ระบบจำลองตรวจจับหมวกนิรภัย + Geofence WebApp
cd /d "%~dp0"

echo =========================================================================
echo   🏍️  เปิดระบบโหมดจำลอง (DEMO MODE)
echo   1. สตาร์ท WebApp Server (http://localhost:5000)
echo   2. เปิดระบบจำลองหน้าปัดรถเสมือนจริง (PC Demo Simulator)
echo =========================================================================
echo.

:: 1. เปิด WebApp Server ในหน้าต่างย่อ (Minimized)
echo [1/3] กำลังสตาร์ท WebApp Server...
start "Helmet Geofence Server" /min python webapp\server.py

:: 2. รอเซิร์ฟเวอร์เริ่มทำงาน 2 วินาที แล้วเปิดเบราว์เซอร์
timeout /t 2 /nobreak > nul
echo [2/3] เปิดหน้าเว็บ Geofence Monitor (http://localhost:5000)...
start http://localhost:5000

:: 3. เปิดโปรแกรมจำลองหน้าปัดรถยนต์ในหน้าต่างหลัก
echo [3/3] กำลังเริ่มโปรแกรมจำลองตรวจจับหมวก (PC Demo)...
echo.
echo =========================================================================
echo   🎮 ปุ่มควบคุมสำหรับสาธิต (เมื่อหน้าต่างจำลองขึ้น):
echo   - [H] : สลับ สวมหมวกนิรภัย / ถอดหมวกนิรภัย
echo   - [W] : เร่งเครื่อง (+5 km/h)
echo   - [S] : เบรก (-10 km/h)
echo   - [E] : เปิด/ปิดคันเร่ง
echo   - [Q] : ออกจากโปรแกรม
echo =========================================================================
echo.

python pc_demo.py

echo.
echo [INFO] ปิดระบบจำลองเรียบร้อยแล้ว กำลังปิด WebApp Server...
taskkill /f /fi "WINDOWTITLE eq Helmet Geofence Server*" > nul 2>&1
echo [DONE] ปิดระบบทั้งหมดเสร็จสมบูรณ์
pause
