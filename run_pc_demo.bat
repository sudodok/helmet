@echo off
chcp 65001 > nul
title ระบบจำลองตรวจจับหมวกกันน็อครถมอเตอร์ไซค์ไฟฟ้า (PC Demo Simulator)
echo =========================================================================
echo  🛵 กำลังเปิดระบบจำลองตรวจจับหมวกกันน็อครถมอเตอร์ไซค์ไฟฟ้า (PC Demo)...
echo =========================================================================
echo.
python pc_demo.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] ไม่สามารถเปิดโปรแกรมได้ กรุณาติดตั้ง dependencies ด้วยคำสั่ง:
    echo pip install -r requirements.txt
    pause
)
