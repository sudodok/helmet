# ระบบตรวจจับหมวกกันน็อคสำหรับรถมอเตอร์ไซค์ไฟฟ้า (EV Motorcycle Smart Helmet Interlock)

ระบบตรวจจับหมวกกันน็อคแบบ Real-time ขับเคลื่อนด้วยบอร์ด **Raspberry Pi 4**, กล้องมุมกว้าง Wide-Angle, โมดูลระบุพิกัดดาวเทียม **GPS ATGM336H (NEO-M8N)** และวงจรควบคุมกล่องคอนโทรลเลอร์มอเตอร์ BLDC พร้อม **เวอร์ชันจำลองสำหรับทดสอบบนคอมพิวเตอร์ (PC Demo Simulator)**

---

## 💻 1. เวอร์ชันทดลองสำหรับคอมพิวเตอร์ (PC / Laptop Demo Version)

เหมาะสำหรับการทดสอบระบบ นำเสนอให้อาจารย์ดู หรือสาธิตการทำงานโดยไม่ต้องยกอุปกรณ์หรือมอเตอร์ไซค์จริงมา:

### วิธีรันบน PC / Laptop:
```bash
# รันผ่านคำสั่ง Python
python pc_demo.py
```
*(หรือบน Windows สามารถดับเบิลคลิกไฟล์ **`run_pc_demo.bat`** เพื่อเปิดได้ทันที)*

### หน้าตาและฟังก์ชันจำลองบน PC:
* **เรือนไมล์ดิจิทัล (EV Speedometer HUD)**: หน้าปัดมาตรวัดความเร็วแบบกราฟิกสวยงาม
* **จำลองฟิสิกส์คันเร่งและเบรก**: กดเร่งความเร็วได้ถึง 60-75 km/h
* **จำลองการตัดความเร็วอัตโนมัติ (Speed Limiter Relay)**: เมื่อไม่สวมหมวก ระบบจะสั่งจำลอง Relay ตัดความเร็วรถลดลงเหลือ **25 km/h** ทันที พร้อมเสียง Buzzer เตือนจริงผ่านลำโพงคอมพิวเตอร์
* **จำลองพิกัดดาวเทียม GPS ATGM336H**: พิกัดขยับเคลื่อนที่ตามความเร็วจริงของรถ
* **ระบบจับเวลาสด (Live Stopwatch & Real-Time Clock)**: แสดงนาฬิกาเวลาจริง `TIME: HH:MM:SS` และระบบจับเวลาสด `STOPWATCH: MM:SS` บน Top Bar, เรือนไมล์ดิจิทัล และประทับลงบนภาพถ่ายหลักฐาน
* **ระบบตรวจจับคน (Person & Helmet Detection)**: ใช้โมเดล YOLOv8n ตรวจจับบุคคลและหมวกกันน็อค พร้อมระบบติดตามพิกัดศีรษะตามหลักกายวิภาค ไม่วูบวาบหรือหลุดกรอบ
* **ระบบบันทึกภาพถ่ายหลักฐานอัจฉริยะ (Smart Event-Driven Captures)**:
  * ⚠️ `no_helmet/`: ตรวจพบไม่สวมหมวกตั้งแต่แรก/ขณะจอด (ตัดระบบสตาร์ท)
  * 🟢 `safe_start/`: สวมหมวกปลดล็อคสตาร์ทรถสำเร็จ (Start Verified)
  * 🚨 `mid_ride_violations/`: แอบถอดหมวกกลางคันขณะขับขี่ (ระบุความเร็วและระยะเวลาที่ขับขี่มาแล้ว)
  * 📸 `manual_snapshots/`: ภาพที่กดถ่ายด้วยตนเองผ่านปุ่ม `[S]`
  * 🌟 `all_captures/` และหน้าแรก `captures/`: รวบรวมภาพถ่ายทุกใบ ทุกเหตุการณ์ไว้ในที่เดียว ไม่ต้องคลิกแยกโฟลเดอร์ย่อย
* **บันทึกภาพถ่ายหลักฐานพร้อมลายน้ำพิกัดและเวลาจับเวลา**: บันทึกภาพลงโฟลเดอร์ `captures/` พร้อมประทับพิกัด GPS, ความเร็ว และเวลา Stopwatch อัตโนมัติ

### ⌨️ คีย์ลัดสำหรับการสาธิต (Demo Keyboard Controls):
| ปุ่มคีย์บอร์ด | การทำงาน |
|:---:|---|
| **`H`** | **สลับสถานะ สวมหมวก / ไม่สวมหมวก (Force Helmet Toggle)** *(แนะนำมากสำหรับการพรีเซนต์)* |
| **`T` หรือ `ลูกศรขึ้น`** | **บิดคันเร่ง (เพิ่มความเร็ว)** |
| **`B` หรือ `ลูกศรลง`** | **แตะเบรก (ลดความเร็ว)** |
| **`S`** | **บันทึกภาพหลักฐานพร้อมลายน้ำพิกัด GPS ทันที** |
| **`M`** | **สลับระหว่างโหมดกล้องเว็บแคมจริง กับ โหมดภาพจำลอง (Synthetic)** |
| **`R`** | **รีเซ็ตสถิติและการละเมิด** |
| **`Q`** | **ออกจากโปรแกรม** |

---

## 🛵 2. เวอร์ชันสำหรับติดตั้งบนตัวรถจริง (Raspberry Pi 4 On-Board)

รันบนบอร์ด **Raspberry Pi 4 Model B** ติดตั้งบนรถมอเตอร์ไซค์ไฟฟ้าจริง ควบคุมผ่านขา GPIO และเชื่อมต่อกับกล่องควบคุมมอเตอร์ BLDC:

```bash
# รันบน Raspberry Pi 4
python helmet_detection.py
```

### 🔌 ตารางการต่อสาย GPIO บน Raspberry Pi 4

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

## 📚 เอกสารประกอบโครงงานทั้งหมด

* 💻 **[pc_demo.py](pc_demo.py)**: โค้ดเวอร์ชันจำลองสำหรับนำเสนอบนคอมพิวเตอร์
* 💬 **[conversation_history.md](conversation_history.md)**: **บันทึกประวัติการพูดคุยและแนวทางตอบข้อซักถามของโครงงาน (Q/A Log)**
* 📖 **[hardware_retrofit_guide.md](hardware_retrofit_guide.md)**: **คู่มือการดัดแปลงและต่อวงจรกับรถมอเตอร์ไซค์ไฟฟ้าจริง** (วงจรภาคจ่ายไฟ 48V-72V, สเต็ปดาวน์, กล่อง Votol/Kelly, สายคันเร่ง Hall Sensor)
* 📑 **[research_document.md](research_document.md)**: **เอกสารวิจัยประกอบโครงงาน 7 บท** (สถิติอุบัติเหตุในไทยปี 2567-2568, กฎหมาย พ.ร.บ. จราจรทางบก, ทฤษฎี YOLO/OpenCV/Edge AI, GPS ATGM336H)
* ⚡ **[arduino/motor_controller.ino](arduino/motor_controller.ino)**: โค้ด Arduino ตัวควบคุมมอเตอร์และอ่านค่า GPS

---

## 🚀 วิธีเปิดใช้งาน (Launcher Scripts)

เลือกเปิดได้ตามการใช้งาน:

### 1. โหมดจำลองสำหรับนำเสนอ (Demo Mode)
ดับเบิลคลิก **[`run_demo.bat`](file:///C:/Users/WINDOWS%20XI/.gemini/antigravity-ide/scratch/helmet-detection-system/run_demo.bat)**
* สตาร์ท WebApp Server อัตโนมัติ (`http://localhost:5000`)
* เปิด Browser ขึ้นมาแสดงหน้า Geofence Monitor ทันที
* เปิดหน้าต่างจำลองหน้าปัดรถยนต์ (`pc_demo.py`)
* ข้อมูลความเร็ว พิกัด และสถานะหมวกจะเชื่อมต่อส่งเข้า WebApp แบบ Real-time!

### 2. โหมดตรวจจับของจริง (Real Hardware Mode)
ดับเบิลคลิก **[`run_real.bat`](file:///C:/Users/WINDOWS%20XI/.gemini/antigravity-ide/scratch/helmet-detection-system/run_real.bat)** (หรือรัน `./run_real.sh` บน Raspberry Pi)
* สตาร์ท WebApp Server อัตโนมัติ
* เปิดระบบตรวจจับกล้องจริง + GPS จริง (`helmet_detection.py`)
* ส่งพิกัดและสถานะจริงเข้า WebApp แบบ Real-time 100% Offline!

---

## 📁 โครงสร้างโปรเจค

```
helmet-detection-system/
├── run_demo.bat                # 🎮 ดับเบิลคลิกเปิดโหมดสาธิต (PC Demo + WebApp)
├── run_real.bat                # ⚡ ดับเบิลคลิกเปิดโหมดของจริง (Hardware + WebApp)
├── run_real.sh                 # 🐧 สคริปต์เปิดโหมดของจริงบน Raspberry Pi 4 (Linux)
├── pc_demo.py                  # 💻 โปรแกรมจำลองและสาธิตสำหรับคอมพิวเตอร์ (PC Demo)
├── helmet_detection.py         # 🛵 โปรแกรมหลักสำหรับติดตั้งบน Raspberry Pi 4 บนรถจริง
├── webapp/                     # 🗺️ ระบบ GPS Geofence Monitor (100% Offline)
│   ├── server.py               # Flask WebSocket Server + Telemetry Bridge
│   ├── geofence.py             # Haversine Distance + Circle Geofence Module
│   └── templates/
│       └── index.html          # Dashboard WebApp (Canvas Map + Live Alerts)
├── conversation_history.md     # 💬 บันทึกประวัติการพูดคุยและตอบข้อซักถามโครงงาน (Q/A)
├── hardware_retrofit_guide.md  # 📖 คู่มือการดัดแปลงระบบไฟและกล่องคอนโทรลเลอร์รถจริง
├── research_document.md       # 📑 เอกสารประกอบโครงงาน 7 บท พร้อมสถิติและงานวิจัย
├── requirements.txt            # รายการ Python dependencies
├── README.md                  # เอกสารแนะนำและคู่มือการใช้งาน
├── arduino/
│   └── motor_controller.ino    # โค้ดไมโครคอนโทรลเลอร์ (Arduino Option)
├── logs/                      # บันทึกประวัติการละเมิดพร้อมพิกัด GPS (JSON)
└── captures/                  # ภาพถ่ายหลักฐานพร้อมลายน้ำพิกัด (JPG)
```
