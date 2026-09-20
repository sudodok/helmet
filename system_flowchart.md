# 📊 แผนผังการทำงานของระบบ (System Flowchart)
## ระบบตรวจจับหมวกนิรภัยสำหรับรถมอเตอร์ไซค์ไฟฟ้า (Smart Helmet Detection & Two-Tier Safety Interlock)

---

## 1. ผังงานรวมการทำงานของระบบ (Overall System Flowchart)

```mermaid
flowchart TD
    Start([🟢 เริ่มต้นการทำงานของระบบ]) --> Init[1. โหลดโมเดล YOLOv8n / Haar Cascade<br>2. เริ่มต้นกล้อง Webcam / CSI<br>3. เชื่อมต่อ GPS ATGM336H & Controller<br>4. ตั้งค่าโฟลเดอร์ captures/ และตัวแปรระบบ]
    
    Init --> ReadSensors[อ่านข้อมูลเฟรมภาพจากกล้อง<br>และอ่านพิกัดความเร็วจากดาวเทียม GPS]
    
    ReadSensors --> AIProcess[ประมวลผลภาพด้วย AI:<br>- ตรวจจับบุคคล Person Detection<br>- ตรวจจับหมวกนิรภัย Helmet Detection<br>- กรองการสั่นไหวด้วย 7-Frame Majority Filter]
    
    AIProcess --> CheckEngine{สถานะรถสตาร์ทแล้วหรือยัง?<br>engine_started == True?}
    
    %% ================= สาขา 1: ก่อนสตาร์ท / รถจอดนิ่ง =================
    CheckEngine -- ยังไม่สตาร์ท (จอดนิ่ง) --> CheckStartHelmet{ตรวจพบการสวมหมวกนิรภัย?<br>is_violation == False?}
    
    CheckStartHelmet -- ไม่สวมหมวก --> LockEngine[⛔ ตัดวงจรสตาร์ท Engine Locked<br>บิดคันเร่งไม่ไป ความเร็ว = 0 km/h<br>ไฟแดงติด LED Red ON]
    LockEngine --> CheckNoHelmetCooldown{ตรวจจับไม่สวมหมวก<br>ครบ Cooldown 5 วิ หรือไม่?}
    CheckNoHelmetCooldown -- ใช่ --> SaveNoHelmet[📸 บันทึกภาพ no_helmet_*.jpg<br>ลง captures/no_helmet/ และ all_captures/<br>ประทับ STOPWATCH: Uptime & TIME]
    CheckNoHelmetCooldown -- ไม่ใช่ / บันทึกแล้ว --> RenderHUD
    SaveNoHelmet --> RenderHUD
    
    CheckStartHelmet -- สวมหมวกถูกต้อง --> UnlockEngine[✅ ปลดล็อคสตาร์ทรถ ENGINE READY<br>เปิดไฟเขียว LED Green ON<br>เริ่มจับเวลาระยะทาง Start Trip Stopwatch]
    UnlockEngine --> CheckStartCaptured{เคยบันทึกภาพสตาร์ทแล้วหรือไม่?}
    CheckStartCaptured -- ยังไม่เคยบันทึก --> SaveSafeStart[📸 บันทึกภาพยืนยัน start_verified_*.jpg<br>ลง captures/safe_start/ และ all_captures/<br>ประทับ STOPWATCH: 00m 00s & TIME]
    CheckStartCaptured -- บันทึกแล้ว --> RenderHUD
    SaveSafeStart --> RenderHUD
    
    %% ================= สาขา 2: รถสตาร์ทแล้ว / กำลังขับขี่ =================
    CheckEngine -- สตาร์ทแล้ว (กำลังขับขี่) --> CheckMidRideHelmet{ตรวจพบการสวมหมวกต่อเนื่อง?<br>is_violation == False?}
    
    CheckMidRideHelmet -- สวมหมวกปกติ --> NormalRide[🟢 โหมดขับขี่ปกติ Normal Riding Mode<br>ปลดล็อคความเร็ว บิดคันเร่งได้เต็มที่<br>ไฟเขียวติด ไซเรนเงียบ]
    NormalRide --> RenderHUD
    
    CheckMidRideHelmet -- ถอดหมวกกลางคัน --> RestrictSpeed[🚨 สั่งรีเลย์จำกัดความเร็วทันที Max 25 km/h<br>เปิดเสียงเตือน Buzzer Beep<br>ไฟแดงเตือนภัยติด LED Red ON]
    RestrictSpeed --> CheckMidRideCooldown{ครบ Cooldown 4 วิ หรือไม่?}
    CheckMidRideCooldown -- ใช่ --> SaveMidRide[📸 บันทึกภาพหลักฐาน mid_ride_*.jpg<br>ลง captures/mid_ride_violations/ และ all_captures/<br>ประทับ STOPWATCH: ระยะเวลาขับขี่ & GPS]
    CheckMidRideCooldown -- ไม่ใช่ / บันทึกแล้ว --> CheckStopStill{ความเร็วลดลงเหลือ 0 km/h<br>และปล่อยคันเร่งหรือไม่?}
    SaveMidRide --> CheckStopStill
    
    CheckStopStill -- ใช่ (จอดนิ่งสนิท) --> ReLock[ล็อคเครื่องยนต์ใหม่ทันที engine_started = False]
    CheckStopStill -- ยังวิ่งอยู่ --> RenderHUD
    ReLock --> RenderHUD
    
    %% ================= ส่วนการแสดงผลและลูป =================
    RenderHUD[วาดหน้าจอแสดงผล Dashboard & HUD:<br>- นาฬิกาเวลาจริง TIME: HH:MM:SS<br>- ระบบจับเวลาสด STOPWATCH: MM:SS<br>- กรอบตรวจจับ Bounding Box & ป้ายชื่อ<br>- หน้าปัดเรือนไมล์ความเร็วดิจิทัล]
    
    RenderHUD --> SendTelemetry[ส่งข้อมูล Telemetry ไร้สาย<br>LoRa 433MHz / WebApp Bridge]
    
    SendTelemetry --> CheckExit{ผู้ใช้กดปุ่ม 'q'<br>เพื่อออกจากโปรแกรมหรือไม่?}
    CheckExit -- ไม่ใช่ --> ReadSensors
    CheckExit -- ใช่ --> End([🔴 สิ้นสุดการทำงาน ปิดอุปกรณ์])
```

---

## 2. ผังงานตรรกะความปลอดภัย 2 ชั้น (Two-Tier Safety Interlock Logic)

```mermaid
flowchart LR
    subgraph Tier1 [🔒 ความปลอดภัยชั้นที่ 1: ระบบตัดสตาร์ทก่อนออกรถ Start Interlock]
        T1_Input[ผู้ขับขี่ขึ้นคร่อมรถ] --> T1_Check{สวมหมวกกันน็อค<br>หรือไม่?}
        T1_Check -- ไม่สวม --> T1_Lock[⛔ ตัดระบบสตาร์ท<br>บิดคันเร่งไม่ไป<br>บันทึกภาพ no_helmet]
        T1_Check -- สวมถูกต้อง --> T1_Unlock[✅ ปลดล็อคสตาร์ท<br>เริ่มจับเวลา Trip Timer<br>บันทึกภาพ safe_start]
    end

    subgraph Tier2 [⚠️ ความปลอดภัยชั้นที่ 2: ระบบจำกัดความเร็วเมื่อถอดกลางคัน Speed Restrictor]
        T1_Unlock --> T2_Ride[ขับขี่บนท้องถนน]
        T2_Ride --> T2_Check{ตรวจพบการถอดหมวก<br>ขณะรถกำลังวิ่งหรือไม่?}
        T2_Check -- สวมหมวกต่อเนื่อง --> T2_Normal[🟢 วิ่งความเร็วปกติได้สูงสุด 60-75 km/h]
        T2_Check -- แอบถอดหมวกกลางคัน --> T2_Limit[🚨 หน่วงเบรก/จำกัดความเร็วเหลือ 25 km/h<br>ส่งเสียง Buzzer เตือน<br>บันทึกภาพ mid_ride_violation<br>พร้อมระบุระยะเวลาที่ขับมาแล้ว]
    end
```

---

## 3. ตารางสถานะการทำงานของระบบ (State Transition Table)

| สถานะของรถ | การตรวจจับหมวก | สวิตช์รีเลย์สตาร์ท | รีเลย์จำกัดความเร็ว | ไฟ LED | เสียงเตือน Buzzer | โฟลเดอร์ที่บันทึกภาพ | ลายน้ำที่ประทับลงภาพ (Watermark) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **ก่อนสตาร์ท / จอดนิ่ง** | ❌ ไม่สวม | **LOCKED (ตัดไฟ)** | ทำงาน (ตัดคันเร่ง) | 🔴 แดง | เงียบ/เตือน | `captures/no_helmet/` | `[ALERT] NO HELMET DETECTED \| STOPWATCH: 00m 25s \| ENGINE LOCKED` |
| **ก่อนสตาร์ท / จอดนิ่ง** | ✅ สวมถูกต้อง | **UNLOCKED (พร้อมขับ)** | ปลดล็อค | 🟢 เขียว | เงียบ | `captures/safe_start/` | `[PASS] SAFE START \| HELMET VERIFIED \| STOPWATCH: 00m 00s` |
| **กำลังขับขี่บนถนน** | ✅ สวมต่อเนื่อง | **UNLOCKED** | ปลดล็อคปกติ | 🟢 เขียว | เงียบ | *(ไม่บันทึกภาพซ้ำ)* | *(ขับขี่ความเร็วปกติ)* |
| **กำลังขับขี่บนถนน** | ❌ แอบถอดกลางคัน | **UNLOCKED** | **ACTIVE (ล็อค 25 km/h)** | 🔴 แดง | **ดังเตือน (BEEP)** | `captures/mid_ride_violations/` | `[ALERT] MID-RIDE HELMET REMOVAL \| STOPWATCH: 02m 15s \| SPEED: 38.5 KM/H` |
| **ทุกสภาวะ** | กดปุ่ม `[S]` | ตามสภาวะขณะนั้น | ตามสภาวะขณะนั้น | ตามสภาวะ | เงียบ | `captures/manual_snapshots/` | `MANUAL SNAPSHOT \| {STATUS} \| STOPWATCH: {TIME}` |

> 💡 **หมายเหตุ**: ทุกภาพที่บันทึกจะถูกทำสำเนาส่งไปยังโฟลเดอร์รวม `captures/all_captures/` โดยอัตโนมัติ เพื่อให้ตรวจสอบรูปภาพทั้งหมดได้ในที่เดียว

---

## 4. คำอธิบายขั้นตอนการทำงานอย่างละเอียด (สำหรับใส่เล่มรายงาน บทที่ 3)

### ขั้นตอนที่ 1: การเตรียมความพร้อมของระบบ (System Initialization)
เมื่อเปิดสวิตช์กุญแจรถมอเตอร์ไซค์ไฟฟ้า บอร์ดประมวลผลจะโหลดโมเดลปัญญาประดิษฐ์ YOLOv8n, เปิดกล้องดิจิทัลมุมกว้าง, เริ่มต้นการเชื่อมต่อดาวเทียม GPS, และสร้างโครงสร้างโฟลเดอร์จัดเก็บหลักฐาน โดยระบบจะตั้งค่าเริ่มต้นให้ **"เครื่องยนต์ถูกล็อค (Engine Locked)"** เสมอเพื่อความปลอดภัย

### ขั้นตอนที่ 2: การประมวลผลภาพและการกรองความผิดพลาด (AI Detection & Noise Filtering)
กล้องจะจับภาพผู้ขับขี่อย่างต่อเนื่องและส่งเข้าสู่โมเดลตรวจจับวัตถุเพื่อค้นหาตำแหน่งบุคคล (Person) และจำแนกศีรษะว่าสวมหมวกนิรภัย (Helmet) หรือไม่สวมหมวก (No Helmet) โดยใช้ **7-Frame Majority Filter** และ **สัดส่วนกายวิภาคศาสตร์มนุษย์ (Anatomical Ratio)** เพื่อลดการสั่นไหวของกรอบและป้องกันการระบุสถานะผิดพลาดจากการกะพริบของแสง

### ขั้นตอนที่ 3: การบังคับใช้ความปลอดภัยชั้นที่ 1 (Start Interlock Enforcement)
- หากผู้ขับขี่ **ไม่สวมหมวกนิรภัย**: รีเลย์จะตัดวงจรคันเร่ง รถไม่สามารถเคลื่อนที่ได้ พร้อมบันทึกภาพหลักฐาน `no_helmet_*.jpg`
- หากผู้ขับขี่ **สวมหมวกนิรภัยถูกต้อง**: ระบบจะปลดล็อคให้สตาร์ทเครื่องยนต์ได้ พร้อมบันทึกภาพยืนยัน `start_verified_*.jpg` และเริ่มนับเวลาจับเวลาการเดินทาง (Live Trip Stopwatch)

### ขั้นตอนที่ 4: การบังคับใช้ความปลอดภัยชั้นที่ 2 ขณะขับขี่ (Mid-Ride Violation Enforcement)
เมื่อรถเริ่มเคลื่อนที่ ระบบจะตรวจสอบการสวมหมวกอย่างต่อเนื่อง:
- หากสวมหมวกตามปกติ ผู้ขับขี่จะสามารถเร่งความเร็วได้ตามขีดจำกัดของรถ
- หากผู้ขับขี่ **แอบถอดหมวกนิรภัยขณะรถกำลังวิ่ง**: ระบบจะสั่งรีเลย์จำกัดความเร็วให้ลดลงเหลือไม่เกิน 25 km/h ทันที เพื่อป้องกันอุบัติเหตุรุนแรง พร้อมส่งเสียงเตือน และบันทึกภาพถ่ายหลักฐาน `mid_ride_*.jpg` ประทับเวลาขับขี่และความเร็วจริงขณะกระทำผิด

### ขั้นตอนที่ 5: การประทับเวลาและส่งข้อมูลโทรมาตร (Telemetry & Logging)
ข้อมูลสถานะ, พิกัด GPS, วันเวลาจริง, และเวลาที่จับเวลาได้จะถูกส่งผ่านคลื่นวิทยุไร้สาย (LoRa / Telemetry Bridge) ไปยังศูนย์ควบคุมหรือหน้าจอแสดงผล และบันทึกลงในล็อกไฟล์ JSON ประจำวันแบบกล่องดำ (Black Box)
