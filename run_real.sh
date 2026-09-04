#!/bin/bash
# =============================================================================
# สคริปต์รันระบบตรวจจับหมวกนิรภัย + Geofence WebApp บน Raspberry Pi 4 (Linux)
# =============================================================================

echo "========================================================================="
echo "  ⚡ เปิดระบบตรวจจับของจริงบน Raspberry Pi 4 (REAL HARDWARE MODE)"
echo "========================================================================="

# ไปยังโฟลเดอร์ของโปรเจกต์
cd "$(dirname "$0")"

# 1. สตาร์ท WebApp Server ในเบื้องหลัง
echo "[1/3] กำลังสตาร์ท WebApp Server (localhost:5000)..."
python3 webapp/server.py &
SERVER_PID=$!

sleep 2

# 2. เปิดเบราว์เซอร์ Chromium ในหน้าจอ RPi (ถ้ามี desktop)
if command -v chromium-browser &> /dev/null; then
    echo "[2/3] เปิดหน้าเว็บ Geofence Monitor..."
    chromium-browser --app=http://localhost:5000 &
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5000 &
fi

# 3. รันโปรแกรมหลัก
echo "[3/3] กำลังเริ่มโปรแกรมตรวจจับหมวกนิรภัย (helmet_detection.py)..."
python3 helmet_detection.py

# เมื่อโปรแกรมหลักหยุด ให้ปิด server ด้วย
echo "[INFO] ปิดระบบเรียบร้อย กำลังปิด WebApp Server..."
kill $SERVER_PID 2>/dev/null
echo "[DONE] เสร็จสมบูรณ์"
