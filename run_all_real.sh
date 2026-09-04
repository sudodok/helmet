#!/bin/bash
# =============================================================================
# สคริปต์เปิดระบบจริงพร้อม WebApp สำหรับ Raspberry Pi / Linux
# =============================================================================
echo "========================================================================="
echo " ⚡ กำลังเปิดระบบจริง (Real Hardware + GPS Geofence WebApp)"
echo "========================================================================="

# 1. รัน WebApp Server ในเบื้องหลัง
python3 webapp/server.py &
SERVER_PID=$!
echo "[INFO] WebApp Server PID: $SERVER_PID"

sleep 2

# 2. เปิด Browser (Chromium) บน Raspberry Pi ถ้ามีจอ
if which chromium-browser > /dev/null 2>&1; then
    chromium-browser --start-fullscreen http://localhost:5000 &
elif which xdg-open > /dev/null 2>&1; then
    xdg-open http://localhost:5000 &
fi

# 3. รันระบบตรวจจับจริง
python3 helmet_detection.py

# 4. เมื่อปิดระบบให้ปิด WebApp Server
kill $SERVER_PID 2>/dev/null
echo "[INFO] ปิดระบบทั้งหมดเรียบร้อย"
