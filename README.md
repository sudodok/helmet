# ระบบตรวจจับหมวกกันน็อคสำหรับรถมอเตอร์ไซค์ไฟฟ้า
# Helmet Detection System for Electric Motorcycles

ระบบตรวจจับหมวกกันน็อคแบบ Real-time สำหรับรถมอเตอร์ไซค์ไฟฟ้า ใช้ OpenCV + YOLO

## ✨ คุณสมบัติ (Features)

1. **การตรวจจับหมวกกันน็อค** - ใช้ YOLO หรือ Haar Cascade (demo mode)
2. **Dashboard แสดงสถานะ** - แสดง FPS, จำนวนเฟรม, การละเมิด
3. **ระบบแจ้งเตือน** - เตือนเมื่อไม่สวมหมวก
4. **การควบคุมความเร็ว** - จำกัดความเร็วผ่าน Serial
5. **บันทึก Log** - บันทึกภาพและข้อมูลการละเมิด
6. **Arduino Code** - สำหรับควบคุมมอเตอร์ไฟฟ้า

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
- **Demo Mode**: ถ้าไม่มีไฟล์ model จะใช้ Haar Cascade + Background Subtraction สำหรับการทดสอบ

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

## 🔌 Arduino/ESP32

โค้ด Arduino สำหรับควบคุมมอเตอร์อยู่ในโฟลเดอร์ `arduino/`

### Pin Configuration

| Pin | Component |
|-----|-----------|
| 9   | Motor PWM |
| 8   | Buzzer    |
| 7   | LED Green |
| 6   | LED Red   |

## 📁 โครงสร้างโปรเจค

```
helmet-detection-system/
├── helmet_detection.py    # ระบบหลัก
├── requirements.txt       # dependencies
├── README.md             # เอกสาร
├── arduino/
│   └── motor_controller.ino  # Arduino code
├── logs/                 # บันทึก log (สร้างอัตโนมัติ)
└── captures/             # ภาพการละเมิด (สร้างอัตโนมัติ)
```
