# ระบบตรวจจับหมวกกันน็อคสำหรับรถมอเตอร์ไซค์ไฟฟ้า
# Helmet Detection System for Electric Motorcycles

ระบบตรวจจับหมวกกันน็อคแบบ Real-time สำหรับรถมอเตอร์ไซค์ไฟฟ้า ใช้ OpenCV + YOLO พร้อมระบบพิกัดดาวเทียม GPS ATGM336H (NEO-M8N)

## ✨ คุณสมบัติ (Features)

1. **การตรวจจับหมวกกันน็อค (Helmet Detection)** - ใช้ YOLO หรือ Haar Cascade (demo mode)
2. **Dashboard HUD แสดงสถานะ** - แสดง FPS, จำนวนเฟรม, สถานะหมวก, ความเร็ว, และพิกัด GPS
3. **ระบบพิกัดดาวเทียม GPS (ATGM336H / NEO-M8N)** - รับสัญญาณผ่านสายอากาศ Active Antenna ระบุพิกัด Latitude, Longitude, ความเร็ว และจำนวนดาวเทียมแบบ Real-time
4. **ประทับลายน้ำพิกัด GPS บนหลักฐาน (Geo-Tagging)** - ประทับพิกัดและวันเวลาลงบนภาพถ่ายการละเมิดโดยอัตโนมัติ
5. **ระบบแจ้งเตือน (Alert System)** - แจ้งเตือนกระพริบบนหน้าจอและส่งสัญญาณเสียง Buzzer
6. **การควบคุมความเร็ว (Speed Control)** - ส่งคำสั่งผ่าน Serial ไปยัง Arduino เพื่อจำกัดความเร็วรถอัตโนมัติเหลือ 25 km/h เมื่อไม่สวมหมวก
7. **บันทึก Log และรายงาน** - บันทึกข้อมูลการละเมิดพร้อมพิกัด GPS ในรูปแบบ JSON
8. **Arduino/ESP32 Controller** - ควบคุมมอเตอร์ PWM, สัญญาณเตือน และอ่านค่าจากโมดูล GPS

## 📦 การติดตั้ง (Installation)

```bash
# ติดตั้ง dependencies
pip install -r requirements.txt
```

## 🚀 วิธีใช้งาน (Usage)

```bash
# รันระบบ
python helmet_detection.py
```

### โหมดการทำงาน

- **YOLO Mode**: ถ้ามีไฟล์ `yolov4-helmet.weights`, `yolov4-helmet.cfg`, `helmet.names` จะใช้ YOLO สำหรับการตรวจจับที่แม่นยำ
- **Demo Mode**: ถ้าไม่มีไฟล์ model จะใช้ Haar Cascade + Background Subtraction สำหรับการทดสอบได้ทันที

### การใช้งานกับ YOLO model จริง

- ต้องฝึก custom YOLO model ด้วยชุดข้อมูลหมวกกันน็อค
- ใช้ dataset เช่น "Helmet Detection Dataset" จาก Kaggle
- หรือใช้ YOLOv8 กับ Ultralytics สำหรับประสิทธิภาพที่ดีกว่า

## ⌨️ คีย์ลัด (Keyboard Shortcuts)

| คีย์ | การทำงาน |
|------|----------|
| `q`  | ออกจากโปรแกรม |
| `s`  | บันทึกภาพหน้าจอ |
| `r`  | รีเซ็ตสถิติ |

## 🔌 วงจรและการต่อสาย Arduino / ESP32

โค้ด Arduino สำหรับควบคุมมอเตอร์และอ่าน GPS อยู่ในโฟลเดอร์ `arduino/motor_controller.ino`

### ตารางการต่อขา (Pin Configuration)

| ขา Arduino | อุปกรณ์ | ขาโมดูล | รายละเอียด |
|------------|---------|---------|------------|
| Pin 9 | Motor Driver | PWM Pin | ควบคุมความเร็วมอเตอร์ |
| Pin 8 | Buzzer | VCC/Signal | สัญญาณเสียงเตือน |
| Pin 7 | LED เขียว | Anode (+) | ไฟเขียว = สวมหมวกนิรภัย |
| Pin 6 | LED แดง | Anode (+) | ไฟแดง = ไม่สวมหมวกนิรภัย |
| Pin 4 | โมดูล GPS ATGM336H | TXD | SoftwareSerial RX (รับพิกัดจาก GPS) |
| Pin 3 | โมดูล GPS ATGM336H | RXD | SoftwareSerial TX |
| 5V / 3.3V | โมดูล GPS ATGM336H | VCC | แรงดันไฟเลี้ยง |
| GND | ทุกอุปกรณ์ | GND | กราวด์ร่วม |

*หมายเหตุ: ต่อสายอากาศ Active Antenna เข้ากับขั้วต่อ IPX บนโมดูล ATGM336H และวางสายอากาศในตำแหน่งที่มองเห็นท้องฟ้าได้ชัดเจน*

## 📁 โครงสร้างโปรเจค

```
helmet-detection-system/
├── helmet_detection.py      # โค้ดหลักระบบตรวจจับ + HUD + จัดการพิกัด GPS
├── requirements.txt         # รายการ dependencies
├── README.md               # เอกสารคู่มือการใช้งาน
├── research_document.md    # เอกสารประกอบโปรเจค 7 บท (สถิติ, กฎหมาย, ทฤษฎี, GPS)
├── arduino/
│   └── motor_controller.ino # โค้ด Arduino คุมมอเตอร์ + อ่าน GPS ATGM336H
├── logs/                   # บันทึก log การละเมิดพร้อมพิกัด (สร้างอัตโนมัติ)
└── captures/               # ภาพหลักฐานการละเมิดพร้อมลายน้ำพิกัด (สร้างอัตโนมัติ)
```
