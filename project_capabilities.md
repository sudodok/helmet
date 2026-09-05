# 🏍️ สรุปความสามารถทั้งหมดของโครงงาน (Project Capabilities)
## ระบบตรวจจับหมวกนิรภัยสำหรับรถมอเตอร์ไซค์ไฟฟ้า
### Smart Helmet Detection & Safety Interlock System for Electric Motorcycles

> **GitHub Repository:** [https://github.com/sudodok/helmet.git](https://github.com/sudodok/helmet.git)  
> **ที่อยู่โปรเจกต์ (Project Path):** `D:\project\helmet-detection-system`  
> **สถานะระบบ:** ใช้งานได้สมบูรณ์ (100% Offline ไม่ต้องพึ่งพาอินเทอร์เน็ตหรือ WiFi)

---

## 📋 1. ภาพรวมโครงงาน (Executive Summary)

โครงงานนี้เป็นระบบ **AI Safety & Telematics System** สำหรับรถมอเตอร์ไซค์ไฟฟ้า (EV Motorcycle) ที่ตรวจจับการสวมหมวกนิรภัยของผู้ขับขี่แบบ Real-time นำผลไปบังคับใช้ **ระบบความปลอดภัย 2 ชั้น (Two-Tier Safety Interlock)** ตัดระบบสตาร์ทและจำกัดความเร็วรถ พร้อมทั้ง **ติดตามพิกัดดาวเทียม GPS** และ **ระบบจำกัดเขตพื้นที่ขับขี่ (Geofence Monitor WebApp)** ที่ทำงานแบบ **100% Offline ภายในเครื่องเดียว**

---

## 🧠 2. ระบบตรวจจับหมวกนิรภัย AI (AI Object Detection Module)
📄 ไฟล์หลัก: [`helmet_detection.py`](file:///D:/project/helmet-detection-system/helmet_detection.py)

| ฟีเจอร์ / หัวข้อ | รายละเอียดการทำงาน |
|---|---|
| **โมเดลที่แนะนำอันดับ 1** | **YOLOv8n (Nano) / YOLOv11n** — ขนาดไฟล์เล็กเพียง **~6 MB** พารามิเตอร์ 3.2 ล้านตัว แม่นยำ mAP50 > 91.5% |
| **Inference Framework บน RPi 4** | **NCNN** (ความเร็วสูงสุด **15–22 FPS**) หรือ **TFLite INT8** (มาตรฐานงานวิจัย ขนาดไฟล์ **~3 MB**, ความเร็ว **12–16 FPS**) |
| **เทคนิคเร่งความเร็ว (Speed Optimization)** | ตั้งค่า Input Resolution เป็น **`imgsz=416`** หรือ **`320`** เพื่อเพิ่มเฟรมเรต 2 เท่า โดยคงความแม่นยำสูงเนื่องจากกล้องจับภาพระยะใกล้ |
| **โมเดลคลาสสิก (OpenCV DNN)** | รองรับ **YOLOv4-Tiny** (`.weights` + `.cfg`) โหลดตรงผ่าน `cv2.dnn.readNetFromDarknet()` |
| **ระบบสำรองอัตโนมัติ (Fallback Demo)** | หากไม่มีไฟล์โมเดล ระบบจะใช้ **Haar Cascade** ตรวจจับใบหน้า + วิเคราะห์ขอบทรงผม/ศีรษะ เพื่อทดสอบระบบได้ทันที |
| **หมวดหมู่ที่ตรวจจับ (Classes)** | 1. `helmet` (สวมหมวกเต็มใบ/ครึ่งใบ) <br> 2. `no_helmet` (ศีรษะเปล่า/หมวกแก๊ป) <br> 3. `person` / `motorcycle` |

---

## 🔐 3. ระบบความปลอดภัย 2 ชั้น (Two-Tier Safety Interlock)
📄 ไฟล์: [`pc_demo.py`](file:///D:/project/helmet-detection-system/pc_demo.py) และ [`helmet_detection.py`](file:///D:/project/helmet-detection-system/helmet_detection.py)

### 🔴 ชั้นที่ 1: ระบบตัดสตาร์ทก่อนออกตัว (Ignition Start Interlock)
* **เงื่อนไข:** เมื่อรถจอดนิ่ง (`ความเร็ว = 0 km/h`) แล้วผู้ขับขี่ **ไม่สวมหมวกนิรภัย**
* **การทำงาน:** ระบบสั่ง Relay ตัดวงจรกล่องสตาร์ท/สายเปิดคันเร่ง ทำให้ **สตาร์ทรถไม่ติดเด็ดขาด บิดคันเร่งไม่ออกตัว (0 km/h)**
* **สถานะแสดงผล:** ขึ้นป้ายเตือนใหญ่กลางจอ `⛔ ENGINE START LOCKED: NO HELMET !` และไฟสถานะสีแดง

### 🟡 ชั้นที่ 2: ระบบจำกัดความเร็วขณะขับขี่ (Dynamic Speed Limiter)
* **เงื่อนไข:** ผู้ขับขี่สตาร์ทรถออกไปแล้ว แต่ระหว่างขับขี่แอบ **ถอดหมวกนิรภัยออก**
* **การทำงาน:** ระบบ **ไม่ตัดไฟกระชากให้ล้อดับทันที** (ป้องกันรถเสียหลักล้มคว่ำ) แต่จะสั่ง Relay ดึงสาย Speed Limit ให้ค่อยๆ ชะลอความเร็วลงและ **ล็อคความเร็วสูงสุดไว้ไม่เกิน 25 km/h**
* **การปลดล็อค:** เมื่อผู้ขับขี่นำหมวกมาสวมศีรษะใหม่ ระบบตรวจจับพบจะปลดล็อคคืนความเร็วเต็มให้ทันทีแบบอัตโนมัติ

---

## 🛰️ 4. ระบบพิกัดดาวเทียมและการประทับหลักฐาน (GPS Telematics)
📄 ไฟล์: [`helmet_detection.py`](file:///D:/project/helmet-detection-system/helmet_detection.py) และ [`arduino/motor_controller.ino`](file:///D:/project/helmet-detection-system/arduino/motor_controller.ino)

| ฟีเจอร์ | รายละเอียดการทำงาน |
|---|---|
| **ฮาร์ดแวร์ GPS** | รองรับ **ATGM336H** และ **U-blox NEO-M8N** สื่อสารผ่านพอร์ต UART 9600 bps |
| **การถอดรหัสพิกัด (NMEA Parsing)** | แยกข้อมูล `$GPGGA`, `$GPRMC`, `$GNVTG`: Latitude, Longitude, ความเร็วดาวเทียม (Ground Speed), จำนวนดาวเทียม |
| **Geo-Tagging Evidence** | ถ่ายภาพผู้กระทำผิด ประทับแถบดำลายน้ำระบุ: **พิกัด Lat/Lon, ความเร็วขณะกระทำผิด, เวลาจับเวลา (Stopwatch), และวันเวลา** บันทึกลงโฟลเดอร์ `captures/` พร้อมโฟลเดอร์รวม `all_captures/` ทันที |
| **อิสระจากสายไมล์รถ** | วัดความเร็วจากดาวเทียม ทำให้ระบบทำงานถูกต้องแม้สายไมล์ที่ล้อรถจะขาดหรือถูกตัดต่อ |

---

## 🗺️ 5. ระบบ GPS Geofence Monitor WebApp (100% Offline)
📄 ไฟล์: [`webapp/server.py`](file:///D:/project/helmet-detection-system/webapp/server.py), [`webapp/geofence.py`](file:///D:/project/helmet-detection-system/webapp/geofence.py), [`webapp/templates/index.html`](file:///D:/project/helmet-detection-system/webapp/templates/index.html)

| ฟีเจอร์ | รายละเอียดการทำงาน |
|---|---|
| **การทำงานแบบออฟไลน์ 100%** | รันบน `localhost:5000` (Local Loopback) ภายในเครื่องเดียว ไม่ต้องต่อ WiFi หรือ Internet |
| **Real-time Telemetry Bridge** | มี Endpoint `/api/telemetry` รับส่งข้อมูลพิกัด, ความเร็ว, สถานะหมวก และสถานะ Engine Lock จากโปรแกรมตรวจจับแบบสดๆ ทุก 0.3 วินาที |
| **แผนที่ Canvas Offline** | วาดแผนที่ Coordinate Grid, จุดศูนย์กลาง, รัศมีวงกลม, ตำแหน่งรถ, และลูกศรทิศทาง โดยใช้ HTML5 Canvas (ไม่พึ่งพา Google Maps API) |
| **คำนวณด้วยสูตร Haversine** | คำนวณระยะห่างระหว่างรถกับจุดศูนย์กลางบนผิวโลกทรงกลม (Earth Radius = 6,371,000 ม.) แม่นยำระดับเมตร |
| **สัญญาณเตือนฉุกเฉิน (Buzzer Alert)** | เมื่อรถวิ่งหลุดออกนอกวงกลม Geofence หน้าเว็บจะแสดงป้ายเตือนกระพริบสีแดงขนาดใหญ่ พร้อมสังเคราะห์เสียง Beep 880Hz ออกลำโพงเครื่อง |
| **ปรับแต่งเขตได้จากหน้าเว็บ** | กรอกพิกัด Latitude, Longitude และรัศมี (เมตร) ได้เอง หรือกดปุ่ม `"📍 ใช้ตำแหน่งปัจจุบัน"` |
| **เส้นทางย้อนหลัง (Trail Tracking)** | วาดเส้นสีฟ้าแสดงเส้นทาง 200 จุดล่าสุดที่รถวิ่งผ่าน |
| **ป้ายสถานะอัจฉริยะ (Smart Pills)** | แสดง `📡 LIVE: PC DEMO SIMULATOR` หรือ `📡 LIVE: HARDWARE SYSTEM (REAL)` และ `⚡ ENGINE READY` / `🔒 ENGINE LOCKED` |

---

## 🔧 6. ระบบฮาร์ดแวร์และการเชื่อมต่อยานพาหนะจริง (Hardware Integration)
📄 ไฟล์: [`hardware_retrofit_guide.md`](file:///D:/project/helmet-detection-system/hardware_retrofit_guide.md) และ [`arduino/motor_controller.ino`](file:///D:/project/helmet-detection-system/arduino/motor_controller.ino)

### 🍓 Raspberry Pi 4 Model B
* **GPIO 17 (Pin 11):** ต่อรีเลย์ตัดสายความเร็วกล่องมอเตอร์ BLDC (Speed Limit / Throttle Inhibit)
* **GPIO 27 (Pin 13):** ต่อ Active Buzzer 5V ส่งเสียงเตือนในตัวรถ
* **GPIO 22 / 23 (Pin 15/16):** หลอดไฟ LED สถานะ (เขียว = ปลอดภัย / แดง = ล็อคความเร็ว)
* **UART GPIO 14/15 (Pin 8/10):** รับสัญญาณพิกัด NMEA จากโมดูล GPS ATGM336H

### ⚡ Arduino Uno / Nano (บอร์ดควบคุมมอเตอร์จำลอง)
* **PWM Pin 9:** ควบคุมสปีดมอเตอร์ BLDC (0–255)
* **SoftwareSerial Pin 3/4:** อ่านข้อมูล GPS จาก ATGM336H ส่งขึ้น Raspberry Pi ผ่าน USB Serial

---

## 💻 7. โปรแกรมจำลองเสมือนจริงบนคอมพิวเตอร์ (PC Demo Simulator)
📄 ไฟล์: [`pc_demo.py`](file:///D:/project/helmet-detection-system/pc_demo.py)

* **HUD หน้าปัดดิจิทัล:** เรือนไมล์เข็มความเร็ว, แถบสถานะแบตเตอรี่ 72V, ไฟแสดงสถานะรีเลย์และเสียงเตือน
* **ฟิสิกส์ยานพาหนะสมจริง:** มีแรงเฉื่อย แรงเสียดทาน และการหน่วงความเร็ว (ไม่ใช่ตัวเลขสุ่มกระโดด)
* **เชื่อมต่อ WebApp อัตโนมัติ:** ส่งข้อมูลความเร็วและพิกัดเข้า WebApp เบื้องหลังแบบ Real-time
* **ป้องกันหน้าต่างค้างบน Windows:** มีตัวดักจับการปิดหน้าต่างกากบาท `[X]` และรองรับการทำงานใน Windows Console

### ⌨️ คีย์ลัดสำหรับการสาธิต (Demo Hotkeys):
| ปุ่มคีย์บอร์ด | ฟังก์ชันการทำงาน |
|:---:|---|
| **`H`** | สลับสถานะ **สวมหมวกนิรภัย / ถอดหมวกนิรภัย** (ใช้พรีเซนต์ทันทีโดยไม่ต้องใส่หมวกจริง) |
| **`T` หรือ `ลูกศรขึ้น`** | บิดคันเร่งเร่งเครื่อง (+5 km/h) |
| **`B` หรือ `ลูกศรลง`** | แตะเบรกชะลอความเร็ว (-10 km/h) |
| **`M`** | สลับระหว่าง **กล้องเว็บแคมจริง** กับ **ภาพจำลอง (Synthetic Frame)** |
| **`S`** | บันทึกภาพหลักฐานพร้อมลายน้ำพิกัด GPS ทันที |
| **`R`** | รีเซ็ตสถิติและการละเมิดทั้งหมด |
| **`Q` หรือ `Esc`** | ออกจากโปรแกรมอย่างปลอดภัย |

---

## 🚀 8. ตัวเปิดระบบและสั่งงาน (Launcher Scripts)

สคริปต์ทั้งหมดถูกเข้ารหัสแบบ **ASCII มาตรฐาน** ป้องกันบั๊ก UTF-8 Parser บน Windows Command Prompt:

| ไฟล์สคริปต์ | ระบบเป้าหมาย | หน้าที่การทำงาน |
|---|:---:|---|
| **[`run_demo.bat`](file:///D:/project/helmet-detection-system/run_demo.bat)** | Windows (คอมพิวเตอร์) | **โหมดสาธิต:** สตาร์ท WebApp Server + เปิด Browser + รัน PC Demo HUD เชื่อมต่อกันทันที |
| **[`run_real.bat`](file:///D:/project/helmet-detection-system/run_real.bat)** | Windows (คอมพิวเตอร์) | **โหมดของจริง:** สตาร์ท WebApp Server + เปิด Browser + รันกล้องตรวจจับจริงและ GPS |
| **[`run_real.sh`](file:///D:/project/helmet-detection-system/run_real.sh)** | Linux (Raspberry Pi 4) | **โหมดของจริงบนรถ:** สคริปต์ Bash รันระบบตรวจจับจริงและเปิดหน้าจอแดชบอร์ดบนตัวรถ |
| **[`run_geofence.bat`](file:///D:/project/helmet-detection-system/run_geofence.bat)** | Windows | เปิดเฉพาะตัวเซิร์ฟเวอร์ Geofence WebApp แบบเดี่ยว |
| **[`run_pc_demo.bat`](file:///D:/project/helmet-detection-system/run_pc_demo.bat)** | Windows | เปิดเฉพาะหน้าปัดจำลอง PC Demo แบบเดี่ยว |

---

## 📁 9. โครงสร้างโปรเจค (Directory Tree)

```
D:\project\helmet-detection-system/
├── run_demo.bat                # 🎮 ดับเบิลคลิกเปิดโหมดสาธิต (PC Demo + WebApp)
├── run_real.bat                # ⚡ ดับเบิลคลิกเปิดโหมดของจริง (Hardware + WebApp)
├── run_real.sh                 # 🐧 สคริปต์เปิดโหมดของจริงบน Raspberry Pi 4 (Linux)
├── run_geofence.bat            # 🗺️ ดับเบิลคลิกเปิดเฉพาะเซิร์ฟเวอร์ WebApp
├── run_pc_demo.bat             # 💻 ดับเบิลคลิกเปิดเฉพาะหน้าปัดจำลอง PC Demo
├── pc_demo.py                  # 💻 โค้ดโปรแกรมจำลองหน้าปัดรถยนต์ (PC Demo Simulator)
├── helmet_detection.py         # 🛵 โค้ดโปรแกรมหลักตรวจจับกล้องจริงสำหรับ Raspberry Pi 4
├── webapp/                     # 🗺️ ระบบ GPS Geofence Monitor (100% Offline)
│   ├── server.py               # Flask WebSocket Server + Telemetry Bridge (/api/telemetry)
│   ├── geofence.py             # โมดูลคำนวณระยะทาง Haversine + วงกลม Geofence
│   └── templates/
│       └── index.html          # หน้า Dashboard WebApp (Canvas Map + Live Telemetry)
├── arduino/
│   └── motor_controller.ino    # โค้ด Arduino ควบคุมมอเตอร์ BLDC และอ่าน GPS
├── captures/                   # โฟลเดอร์จัดเก็บภาพหลักฐาน (GPS & Stopwatch Watermarked)
│   ├── all_captures/           # 🌟 โฟลเดอร์รวมทุกภาพ ไม่แยกหมวดหมู่ เปิดดูได้ครบจบในที่เดียว
│   ├── no_helmet/              # ⚠️ ภาพตรวจพบไม่สวมหมวกก่อนออกรถ / ขณะจอด (ตัดสตาร์ท)
│   ├── safe_start/             # 🟢 ภาพยืนยันการสวมหมวกออกรถสำเร็จ (Start Verified)
│   ├── mid_ride_violations/    # 🚨 ภาพถอดหมวกกลางคันขณะขับขี่ (พร้อมระบุเวลาขับขี่)
│   └── manual_snapshots/       # 📸 ภาพที่กดบันทึกด้วยตนเองผ่านปุ่ม [S]
├── logs/                      # โฟลเดอร์เก็บรายงานสถิติและประวัติออกนอกเขต (JSON)
├── conversation_history.md     # 💬 บันทึกประวัติการพูดคุยและตอบคำถามเชิงเทคนิค 18 หัวข้อ
├── hardware_retrofit_guide.md # 📖 คู่มือการต่อวงจรและดัดแปลงระบบไฟกับรถมอเตอร์ไซค์ไฟฟ้าจริง
├── research_document.md       # 📑 เอกสารวิจัยประกอบโครงงาน 7 บท (สถิติ, กฎหมาย, ทฤษฎี, GPS)
├── requirements.txt            # รายการไลบรารีที่จำเป็น (OpenCV, numpy, Flask, SocketIO)
└── README.md                  # คู่มือแนะนำการติดตั้งและใช้งานภาพรวม
```

---
*เอกสารนี้จัดทำขึ้นและปรับปรุงล่าสุดสำหรับอ้างอิงความสามารถทางวิชาการและเทคนิคของโครงงาน*
