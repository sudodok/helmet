# ระบบตรวจจับหมวกกันน็อคสำหรับรถมอเตอร์ไซค์ไฟฟ้า (ติดตั้งบนรถจริง)
# Helmet Detection System for Electric Motorcycles (Raspberry Pi 4 & Real EV Retrofit)

ระบบตรวจจับหมวกกันน็อคแบบ Real-time ติดตั้งบน **รถมอเตอร์ไซค์ไฟฟ้าจริง** ขับเคลื่อนด้วยบอร์ด **Raspberry Pi 4**, กล้องมุมกว้าง Wide-Angle, โมดูลระบุพิกัดดาวเทียม **GPS ATGM336H (NEO-M8N)** และวงจรควบคุมกล่องคอนโทรลเลอร์มอเตอร์ BLDC

---

## ✨ คุณสมบัติเด่น (Key Features)

1. **รองรับบอร์ดประมวลผล Raspberry Pi 4 Model B**: ทำงานแบบ Edge AI บนตัวรถมอเตอร์ไซค์ไฟฟ้าจริง ไม่ต้องพึ่งพาสัญญาณอินเทอร์เน็ตในการตรวจจับ
2. **การตรวจจับหมวกกันน็อค Real-time**: ตรวจจับและจำแนก Class `helmet` และ `no_helmet` บนภาพสตรีมจากกล้องมุมกว้าง
3. **ระบบตัดต่อ/จำกัดความเร็วรถจริง (Speed Limiting Interlock)**: 
   - สั่งงาน Relay / Optocoupler ผ่าน GPIO 17 ไปยังสาย **Speed Limit Wire** ของกล่องมอเตอร์ (เช่น Votol, Kelly, กล่องติดรถ)
   - หากไม่สวมหมวก รถจะถูกล็อคความเร็วอัตโนมัติไม่เกิน **25 km/h**
4. **ระบบระบุพิกัดดาวเทียม GPS ATGM336H (NEO-M8N)**:
   - เชื่อมต่อสายอากาศ Active Ceramic Antenna พร้อม LNA
   - บันทึกพิกัด Latitude, Longitude, ความเร็ว และจำนวนดาวเทียม
5. **ประทับลายน้ำหลักฐาน (Geo-Tagging Evidence)**: บันทึกภาพถ่ายการละเมิดพร้อมป้ายแถบลายน้ำระบุพิกัด GPS และวันเวลาลงบนภาพโดยอัตโนมัติ
6. **ระบบแจ้งเตือนรอบด้าน**: เสียง Active Buzzer และไฟ LED แจ้งเตือนบนแฮนด์รถ
7. **เอกสารคู่มือดัดแปลงรถจริงฉบับสมบูรณ์**: อธิบายวิธีต่อสายไฟกับแบตเตอรี่แรงดันสูง (48V-72V), การแปลงไฟ DC-DC, และการต่อสายคันเร่ง

---

## 📦 การติดตั้งบน Raspberry Pi 4 (Installation)

```bash
# 1. ติดตั้ง System Dependencies บน Raspberry Pi OS
sudo apt-get update
sudo apt-get install -y python3-opencv python3-pip libatlas-base-dev

# 2. ติดตั้ง Python Libraries
pip install -r requirements.txt
```

---

## 🚀 วิธีเปิดใช้งาน (Usage)

```bash
# รันโปรแกรมหลัก
python helmet_detection.py
```

*โปรแกรมจะตรวจจับอัตโนมัติ: หากรันบน Raspberry Pi 4 จะเปิดระบบควบคุม GPIO และ UART ให้ทันที หรือหากรันบน PC ทั่วไปจะเปิดโหมดจำลอง (Simulation Mode) เพื่อทดสอบได้โดยไม่ต้องต่อฮาร์ดแวร์จริง*

---

## 🔌 ตารางการต่อสาย GPIO บน Raspberry Pi 4

| ขาทางกายภาพ (Physical Pin) | ขา GPIO | อุปกรณ์ที่ต่อ | หน้าที่การทำงาน |
|:---:|:---:|---|---|
| **Pin 11** | **GPIO 17** | **Relay Module (IN)** | สั่งตัดต่อสาย Speed Limit ของกล่องมอเตอร์ |
| **Pin 13** | **GPIO 27** | **Active Buzzer (+)** | สัญญาณเสียงเตือนเมื่อไม่สวมหมวก |
| **Pin 15** | **GPIO 22** | **LED เขียว (+)** | ไฟสถานะสวมหมวกนิรภัย (ปลอดภัย) |
| **Pin 16** | **GPIO 23** | **LED แดง (+)** | ไฟสถานะไม่สวมหมวกนิรภัย (อันตราย) |
| **Pin 8** | **GPIO 14 (TXD)** | **GPS ATGM336H (RXD)** | สื่อสารตั้งค่า GPS |
| **Pin 10** | **GPIO 15 (RXD)** | **GPS ATGM336H (TXD)** | รับข้อมูลพิกัด NMEA จาก GPS |
| **Pin 2 / 4** | **5V Power** | **VCC Relay, GPS, Buzzer** | ไฟเลี้ยงอุปกรณ์ 5V |
| **Pin 6 / 9** | **GND** | **GND รวม** | กราวด์ร่วมระบบ |

---

## 📚 เอกสารประกอบโครงงานและคู่มือฮาร์ดแวร์

* 📖 [hardware_retrofit_guide.md](hardware_retrofit_guide.md): **คู่มือการดัดแปลงและต่อวงจรกับรถมอเตอร์ไซค์ไฟฟ้าจริง** (วงจรภาคจ่ายไฟ 48V-72V, สเต็ปดาวน์, กล่อง Votol/Kelly, สายคันเร่ง Hall Sensor)
* 📑 [research_document.md](research_document.md): **เอกสารวิจัยประกอบโครงงาน 7 บท** (สถิติอุบัติเหตุในไทยปี 2567-2568, กฎหมาย พ.ร.บ. จราจรทางบก, ทฤษฎี YOLO/OpenCV/Edge AI, GPS ATGM336H)
* ⚡ [arduino/motor_controller.ino](arduino/motor_controller.ino): โค้ดสำรองสำหรับกรณีที่ต้องการใช้ Arduino เป็นโมดูลควบคุมมอเตอร์แยก

---

## 📁 โครงสร้างโปรเจค

```
helmet-detection-system/
├── helmet_detection.py         # โปรแกรมหลักตรวจจับ AI + คุม GPIO บน Raspberry Pi 4
├── hardware_retrofit_guide.md # คู่มือดัดแปลงระบบไฟและกล่องคอนโทรลเลอร์รถจริง
├── research_document.md       # เอกสารประกอบโครงงาน 7 บท พร้อมสถิติและงานวิจัย
├── requirements.txt            # รายการ Python dependencies
├── README.md                  # เอกสารแนะนำและคู่มือการใช้งาน
├── arduino/
│   └── motor_controller.ino    # โค้ดไมโครคอนโทรลเลอร์ (Arduino Option)
├── logs/                      # บันทึกประวัติการละเมิดพร้อมพิกัด GPS (JSON)
└── captures/                  # ภาพถ่ายหลักฐานพร้อมลายน้ำพิกัด (JPG)
```
