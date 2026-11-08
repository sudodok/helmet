#!/bin/bash
# =============================================================================
# สคริปต์ตั้งค่าความเร็วสูงสุด (Max FPS Optimization) บน Raspberry Pi 4 / 5
# =============================================================================

echo "========================================================================="
echo "  🚀 เริ่มต้นปรับแต่งระบบ Raspberry Pi ให้ได้ FPS สูงที่สุด"
echo "========================================================================="

# 1. ตั้งค่า CPU Governor เป็น Performance (ไม่ให้ชิปลดความถี่สัญญาณนาฬิกา)
echo "[1/4] ปรับตั้งค่าโหมดซีพียูเป็น Performance..."
if [ -d "/sys/devices/system/cpu/cpu0/cpufreq" ]; then
    echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null
    echo "      ✔️ ตั้งค่า CPU Governor = performance เรียบร้อย"
else
    echo "      ℹ️ ข้ามขั้นตอน CPU scaling (ไม่มี cpufreq)"
fi

# 2. แตกไฟล์ NCNN Model (หากมีไฟล์ zip ที่ดาวน์โหลดมาจาก Colab)
echo "[2/4] ตรวจสอบและแตกไฟล์โมเดล NCNN..."
cd "$(dirname "$0")"

if [ -f "best_ncnn_model.zip" ]; then
    echo "      📦 พบไฟล์ best_ncnn_model.zip กำลังแตกไฟล์..."
    unzip -o best_ncnn_model.zip
    echo "      ✔️ แตกไฟล์โมเดล NCNN เรียบร้อย"
elif [ -d "best_ncnn_model" ]; then
    echo "      ✔️ พบโฟลเดอร์โมเดล NCNN (best_ncnn_model) พร้อมใช้งานแล้ว"
else
    echo "      ⚠️ ยังไม่พบโฟลเดอร์ best_ncnn_model (จะใช้ best.pt หรือโหมดสำรอง)"
fi

# 3. ติดตั้ง Dependencies สำหรับรัน High-FPS
echo "[3/4] ตรวจสอบ Library ที่จำเป็น..."
pip3 install -q ultralytics

# 4. แสดงสถานะความเร็วและอุณหภูมิปัจจุบัน
echo "[4/4] สถานะปัจจุบันของบอร์ด Raspberry Pi:"
if command -v vcgencmd &> /dev/null; then
    echo "      🌡️ อุณหภูมิ CPU: $(vcgencmd measure_temp)"
    echo "      ⚡ ความถี่ CPU:  $(vcgencmd measure_clock arm)"
fi

echo "========================================================================="
echo "  ✨ พร้อมเริ่มทำงาน! กำลังสตาร์ท helmet_detection.py ในโหมด High FPS..."
echo "========================================================================="

python3 helmet_detection.py

