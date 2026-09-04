# 🏍️ สรุปความสามารถทั้งหมดของโครงงาน
## ระบบตรวจจับหมวกกันน็อคสำหรับรถมอเตอร์ไซค์ไฟฟ้า
### Helmet Detection System for Electric Motorcycles

> **GitHub:** https://github.com/sudodok/helmet.git

---

## 📋 ภาพรวมโครงงาน

โครงงานนี้เป็นระบบ **AI Safety System** สำหรับรถมอเตอร์ไซค์ไฟฟ้า ที่ตรวจจับว่าผู้ขับขี่สวมหมวกกันน็อคหรือไม่ แล้วนำผลไปบังคับใช้ **ระบบความปลอดภัย 2 ชั้น** (Two-Tier Safety Interlock) และ **ติดตามพิกัด GPS** พร้อม **Geofence Monitor WebApp** ทั้งหมดทำงาน **100% Offline**

---

## 🧠 Module 1: ระบบตรวจจับหมวกกันน็อค (AI Detection)
📄 ไฟล์: [`helmet_detection.py`](file:///C:/Users/WINDOWS%20XI/.gemini/antigravity-ide/scratch/helmet-detection-system/helmet_detection.py)

| ฟีเจอร์ | รายละเอียด |
|---|---|
| **YOLO Object Detection** | ใช้ YOLOv4 ตรวจจับ 4 คลาส: `helmet`, `no_helmet`, `person`, `motorcycle` |
| **GPU Acceleration** | รองรับ CUDA GPU (ถ้ามี) หรือ CPU fallback อัตโนมัติ |
| **Demo Mode (Fallback)** | ถ้าไม่มีไฟล์ model → ใช้ **Haar Cascade** ตรวจจับใบหน้า + Background Subtractor |
| **Confidence Threshold** | กรองผลลัพธ์ด้วย threshold 50% + NMS 40% ป้องกัน False Positive |
| **Real-time Processing** | ประมวลผล 1280×720 ได้ ~21 FPS บน CPU ทั่วไป |

---

## 🔐 Module 2: ระบบความปลอดภัย 2 ชั้น (Two-Tier Safety Interlock)
📄 ไฟล์: [`pc_demo.py`](file:///C:/Users/WINDOWS%20XI/.gemini/antigravity-ide/scratch/helmet-detection-system/pc_demo.py) + [`helmet_detection.py`](file:///C:/Users/WINDOWS%20XI/.gemini/antigravity-ide/scratch/helmet-detection-system/helmet_detection.py)

### ชั้นที่ 1: ระบบตัดสตาร์ท (Ignition Start Interlock)
| ฟีเจอร์ | รายละเอียด |
|---|---|
| **ล็อคสตาร์ท** | ถ้าไม่สวมหมวกตั้งแต่แรก → **สตาร์ทรถไม่ติด** บิดคันเร่งไม่ไป |
| **ปลดล็อค** | ต้องสวมหมวกก่อน → ระบบตรวจพบ → ปลดล็อคให้สตาร์ทได้ |
| **Engine Ready** | แสดงสถานะ `ENGINE READY` เมื่อปลดล็อคสำเร็จ |
| **Engine Locked** | แสดงสถานะ `ENGINE LOCKED` เมื่อยังไม่สวมหมวก |

### ชั้นที่ 2: จำกัดความเร็ว (Speed Limiter)
| ฟีเจอร์ | รายละเอียด |
|---|---|
| **จำกัดที่ 25 km/h** | ถ้าสตาร์ทได้แล้วแต่ระหว่างขับ **ถอดหมวก** → ระบบจำกัดความเร็วไม่เกิน 25 km/h |
| **ควบคุมผ่าน Relay** | GPIO 17 ตัดสัญญาณคันเร่ง / จำกัดค่า PWM ให้ BLDC Controller |
| **คืนค่าอัตโนมัติ** | สวมหมวกกลับ → ปลดล็อคความเร็วเต็มทันที |

---

## 🛰️ Module 3: ระบบนำทาง GPS (ATGM336H)
📄 ไฟล์: [`helmet_detection.py`](file:///C:/Users/WINDOWS%20XI/.gemini/antigravity-ide/scratch/helmet-detection-system/helmet_detection.py) + [`arduino/motor_controller.ino`](file:///C:/Users/WINDOWS%20XI/.gemini/antigravity-ide/scratch/helmet-detection-system/arduino/motor_controller.ino)

| ฟีเจอร์ | รายละเอียด |
|---|---|
| **โมดูล GPS** | รองรับ **ATGM336H** / **NEO-M8N** (สื่อสารผ่าน UART 9600 baud) |
| **NMEA Parsing** | แยกข้อมูลจาก `$GPGGA`, `$GPRMC` ได้: Latitude, Longitude, ความเร็ว, จำนวนดาวเทียม |
| **พิกัดแบบ Real-time** | อัปเดตตำแหน่งทุก 1 วินาที |
| **Geo-tagging หลักฐาน** | ประทับพิกัด GPS บนภาพหลักฐานเมื่อตรวจพบการละเมิด |
| **Arduino Integration** | Arduino อ่าน GPS โดยตรงผ่าน SoftwareSerial แล้วส่งข้อมูลไปยัง RPi ผ่าน USB Serial |

---

## 🗺️ Module 4: ระบบ GPS Geofence Monitor WebApp (100% Offline)
📄 ไฟล์: [`webapp/server.py`](file:///C:/Users/WINDOWS%20XI/.gemini/antigravity-ide/scratch/helmet-detection-system/webapp/server.py) + [`webapp/geofence.py`](file:///C:/Users/WINDOWS%20XI/.gemini/antigravity-ide/scratch/helmet-detection-system/webapp/geofence.py) + [`webapp/templates/index.html`](file:///C:/Users/WINDOWS%20XI/.gemini/antigravity-ide/scratch/helmet-detection-system/webapp/templates/index.html)

| ฟีเจอร์ | รายละเอียด |
|---|---|
| **100% Offline** | ทำงานบน localhost ไม่ต้องต่อ WiFi หรือ Internet เลย |
| **แผนที่ Canvas** | วาดด้วย HTML5 Canvas ไม่พึ่ง Google Maps มีกริดพิกัด Lat/Lon |
| **วงกลม Geofence** | กำหนดเขตเป็นวงกลม (จุดศูนย์กลาง + รัศมีเมตร) ปรับได้จากหน้าเว็บ |
| **Haversine Distance** | คำนวณระยะทางจริงบนผิวโลกทรงกลม ด้วยสูตร Haversine |
| **Real-time WebSocket** | อัปเดตตำแหน่งรถผ่าน WebSocket ทุก 0.5 วินาที |
| **จุดตำแหน่งรถ** | จุดกระพริบสีเขียว (อยู่ในเขต) / สีแดง (นอกเขต) + ลูกศรทิศทาง |
| **เส้นทาง Trail** | แสดง 200 จุดล่าสุดที่รถวิ่งผ่านเป็นเส้นสีฟ้า |
| **ป้ายเตือน ⛔** | แถบสีแดงกระพริบขนาดใหญ่เมื่อรถออกนอกเขต |
| **เสียงเตือน Buzzer** | เสียง Beep 880Hz จากลำโพงทุก 1 วินาทีเมื่อนอกเขต |
| **ตั้งค่าเขตจากหน้าเว็บ** | เปลี่ยนจุดศูนย์กลาง + รัศมีได้ทันที หรือกด "ใช้ตำแหน่งปัจจุบัน" |
| **Log ออกนอกเขต** | บันทึก JSON ทุกครั้งที่ออกนอกเขตพร้อมเวลา + พิกัด + ความเร็ว |
| **แดชบอร์ดสถานะ** | แสดง: ความเร็ว, พิกัด, จำนวนดาวเทียม, ทิศทาง, สถานะหมวก, สถานะ Geofence |

---

## 🔧 Module 5: ระบบฮาร์ดแวร์ (Hardware Integration)
📄 ไฟล์: [`arduino/motor_controller.ino`](file:///C:/Users/WINDOWS%20XI/.gemini/antigravity-ide/scratch/helmet-detection-system/arduino/motor_controller.ino) + [`hardware_retrofit_guide.md`](file:///C:/Users/WINDOWS%20XI/.gemini/antigravity-ide/scratch/helmet-detection-system/hardware_retrofit_guide.md)

### Raspberry Pi 4 Model B
| ฟีเจอร์ | รายละเอียด |
|---|---|
| **กล้อง Pi Camera** | รับภาพ 1280×720 @ 30 FPS |
| **GPIO 17 → Relay** | ควบคุมรีเลย์ตัดสัญญาณคันเร่ง / ล็อคสตาร์ท |
| **GPIO 27 → Buzzer** | ขับเสียงเตือน Active Buzzer 5V |
| **GPIO 22 → LED เขียว** | ไฟแสดงสถานะ "ปลอดภัย" |
| **GPIO 23 → LED แดง** | ไฟแสดงสถานะ "อันตราย" |
| **UART → GPS** | อ่าน GPS ATGM336H ผ่าน `/dev/ttyAMA0` |

### Arduino Uno/Nano
| ฟีเจอร์ | รายละเอียด |
|---|---|
| **PWM Pin 9** | ควบคุมความเร็วมอเตอร์ BLDC (0-255) |
| **Pin 8 → Buzzer** | เสียงเตือน |
| **Pin 7 → LED Green** | สถานะปลอดภัย |
| **Pin 6 → LED Red** | สถานะอันตราย |
| **Pin 3,4 → GPS** | SoftwareSerial อ่าน ATGM336H |
| **USB Serial** | รับคำสั่ง JSON จาก RPi (`{"helmet": true}`) |

---

## 💻 Module 6: PC Demo Simulator (เวอร์ชันนำเสนอ)
📄 ไฟล์: [`pc_demo.py`](file:///C:/Users/WINDOWS%20XI/.gemini/antigravity-ide/scratch/helmet-detection-system/pc_demo.py) + [`run_pc_demo.bat`](file:///C:/Users/WINDOWS%20XI/.gemini/antigravity-ide/scratch/helmet-detection-system/run_pc_demo.bat)

| ฟีเจอร์ | รายละเอียด |
|---|---|
| **หน้าปัด HUD** | Speedometer วงกลม, มาตรแบตเตอรี่ 72V, ไฟสถานะ LED จำลอง |
| **ฟิสิกส์จำลอง** | แรงเสียดทาน, ลมต้าน, ความเร่ง/ชะลอจริง (ไม่ใช่เลขกระโดด) |
| **คันเร่ง/เบรก** | ปุ่ม W = เร่ง, S = เบรก, ปรับความเร็วเป้าหมายได้ |
| **Webcam จริง** | ใช้กล้อง Webcam ตรวจจับใบหน้าจริง → ถ้ามีหน้า ≈ สวมหมวก |
| **โหมดไม่มีกล้อง** | สร้างภาพจำลองผู้ขับขี่อัตโนมัติ (Synthetic Frame) |
| **จำลอง GPS** | เลื่อนพิกัดตามทิศทางและความเร็วจริง |
| **บันทึกภาพหลักฐาน** | ถ่ายภาพ + ประทับ GPS ลง `captures/` ทุกครั้งที่ละเมิด |
| **เสียงเตือนจริง** | ใช้ `winsound.Beep()` ส่งเสียงจากลำโพงคอมจริง |
| **สรุปผลทดสอบ** | เมื่อปิดโปรแกรม → แสดง Report: จำนวนเฟรม, FPS, ครั้งที่ละเมิด, พิกัดสุดท้าย |

### ⌨️ คีย์ลัดสำหรับสาธิต (Demo Hotkeys)
| ปุ่ม | ฟังก์ชัน |
|:---:|---|
| `H` | สลับ สวมหมวก / ไม่สวมหมวก |
| `W` | เร่งเครื่อง (เพิ่มความเร็วเป้าหมาย +5 km/h) |
| `S` | เบรก (ลดความเร็วเป้าหมาย -10 km/h) |
| `E` | เปิด/ปิดคันเร่ง |
| `Q` | ออกจากโปรแกรม |

---

## 📊 Module 7: ระบบบันทึกข้อมูลและหลักฐาน (Data Logging)

| ประเภทข้อมูล | รูปแบบ | ที่เก็บ |
|---|---|---|
| **ภาพหลักฐานการละเมิด** | `.jpg` + GPS watermark | `captures/violation_YYYYMMDD_HHMMSS.jpg` |
| **Log การออกนอกเขต Geofence** | `.json` (timestamp, lat/lon, speed) | `logs/geofence_alerts_YYYYMMDD.json` |
| **สถิติการทำงาน** | Console output | เมื่อปิดโปรแกรม pc_demo |

---

## 📁 โครงสร้างไฟล์ทั้งหมด

```
helmet-detection-system/
├── helmet_detection.py         # ระบบหลัก (YOLO + GPIO + GPS) สำหรับ Raspberry Pi
├── pc_demo.py                  # เวอร์ชันจำลองบน PC (สำหรับนำเสนอ)
├── run_pc_demo.bat             # ดับเบิลคลิกเปิด PC Demo
├── run_geofence.bat            # ดับเบิลคลิกเปิด Geofence WebApp
├── requirements.txt            # Dependencies (opencv, numpy, flask, socketio)
├── README.md                   # คู่มือการใช้งาน
├── research_document.md        # เอกสารวิจัย
├── hardware_retrofit_guide.md  # คู่มือประกอบฮาร์ดแวร์ + แผนผังวงจร
├── conversation_history.md     # ประวัติการพัฒนาและ Q&A
├── arduino/
│   └── motor_controller.ino    # โค้ด Arduino ควบคุมมอเตอร์ + GPS
├── webapp/
│   ├── server.py               # Flask server (Geofence Monitor)
│   ├── geofence.py             # Haversine + Circle Geofence
│   └── templates/
│       └── index.html          # Dashboard WebApp (Canvas map + alerts)
├── captures/                   # ภาพหลักฐานการละเมิด
└── logs/                       # Log files (JSON)
```

---

## 🏗️ สถาปัตยกรรมระบบ

```
┌───────────────────────────────────────────────────────────────────┐
│                    ผู้ขับขี่ (Rider)                                │
│                         │                                        │
│                    📷 กล้อง Pi Camera                              │
│                         │                                        │
│                 ┌───────▼────────┐                                │
│                 │  🧠 AI Engine   │                                │
│                 │ YOLO / Haar    │                                │
│                 │ Cascade        │                                │
│                 └──┬──────┬──┬──┘                                │
│                    │      │  │                                    │
│            ┌───────▼──┐ ┌▼──▼───────┐  ┌──────────────────────┐  │
│            │ Tier 1:  │ │ Tier 2:   │  │ 🛰️ GPS ATGM336H      │  │
│            │ ตัดสตาร์ท │ │ จำกัด 25  │  │ → พิกัด + ความเร็ว    │  │
│            │ (Relay)  │ │ km/h      │  │ → Geofence Check     │  │
│            └──────────┘ └───────────┘  └──────────┬───────────┘  │
│                                                   │              │
│            ┌──────────────────────────────────────▼──────────┐   │
│            │ 🗺️ WebApp Dashboard (localhost:5000)             │   │
│            │ → แผนที่ Canvas + วงกลม Geofence                 │   │
│            │ → ป้ายเตือน ⛔ + เสียง Buzzer เมื่อออกนอกเขต      │   │
│            │ → ตั้งค่าเขตพื้นที่ได้จากหน้าเว็บ                  │   │
│            └────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

---

## ⚡ วิธีเปิดใช้งาน

### PC Demo (คอมพิวเตอร์ — สำหรับนำเสนอ)
```bash
# ดับเบิลคลิก run_pc_demo.bat หรือ:
python pc_demo.py
```

### Geofence WebApp (ดูแผนที่ + เตือนออกนอกเขต)
```bash
# ดับเบิลคลิก run_geofence.bat หรือ:
python webapp/server.py
# → เปิด Browser ที่ http://localhost:5000
```

### Raspberry Pi (ระบบจริงบนรถ)
```bash
python helmet_detection.py
```
