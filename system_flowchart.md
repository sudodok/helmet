# 📊 แผนผังการทำงานของระบบ (System Flowchart)
## ระบบตรวจจับหมวกนิรภัยสำหรับรถมอเตอร์ไซค์ไฟฟ้า (Smart Helmet Detection & Safety Alert System)

---

## 1. ผังงานรวมการทำงานของระบบ (Overall System Flowchart)

```mermaid
flowchart TD
    Start(["🟢 เริ่มต้นการทำงานของระบบ"]) --> Init["1. โหลดโมเดล YOLOv8n / Haar Cascade<br/>2. เริ่มต้นกล้องตรวจจับผู้ขับขี่<br/>3. เชื่อมต่อตัวควบคุมวงจร Controller / Relay<br/>4. ตั้งค่าโฟลเดอร์ captures/ และตัวแปรระบบ"]
    
    Init --> ReadCamera["อ่านข้อมูลเฟรมภาพจากกล้องตรวจจับผู้ขับขี่"]
    
    ReadCamera --> AIProcess["ประมวลผลภาพด้วย AI:<br/>- ตรวจจับบุคคล Person Detection<br/>- ตรวจจับหมวกนิรภัย Helmet Detection<br/>- กรองการสั่นไหวด้วย 7-Frame Majority Filter"]
    
    AIProcess --> CheckEngine{"สถานะรถสตาร์ทแล้วหรือยัง?<br/>engine_started == True?"}
    
    %% ================= สาขา 1: ก่อนสตาร์ท / รถจอดนิ่ง =================
    CheckEngine -->|"ยังไม่สตาร์ท (จอดนิ่ง)"| CheckStartHelmet{"ตรวจพบการสวมหมวกนิรภัย?<br/>is_violation == False?"}
    
    CheckStartHelmet -->|"ไม่สวมหมวก"| LockEngine["⛔ ตัดวงจรสตาร์ท Engine Locked<br/>บิดคันเร่งไม่ไป รถไม่สามารถออกตัวได้<br/>ไฟแดงติด LED Red ON"]
    LockEngine --> CheckNoHelmetCooldown{"ตรวจจับไม่สวมหมวก<br/>ครบ Cooldown 5 วิ หรือไม่?"}
    CheckNoHelmetCooldown -->|"ใช่"| SaveNoHelmet["📸 บันทึกภาพ no_helmet_*.jpg<br/>ลง captures/no_helmet/ และ all_captures/<br/>ประทับเวลาจับเวลาระบบ STOPWATCH & TIME"]
    CheckNoHelmetCooldown -->|"ไม่ใช่ หรือ บันทึกแล้ว"| RenderHUD
    SaveNoHelmet --> RenderHUD
    
    CheckStartHelmet -->|"สวมหมวกถูกต้อง"| UnlockEngine["✅ ปลดล็อคสตาร์ทรถ ENGINE READY<br/>เปิดไฟเขียวปลอดภัย LED Green ON<br/>เริ่มจับเวลาขับขี่ Start Trip Stopwatch"]
    UnlockEngine --> CheckStartCaptured{"เคยบันทึกภาพสตาร์ทแล้วหรือไม่?"}
    CheckStartCaptured -->|"ยังไม่เคยบันทึก"| SaveSafeStart["📸 บันทึกภาพยืนยัน start_verified_*.jpg<br/>ลง captures/safe_start/ และ all_captures/<br/>ประทับ STOPWATCH: 00m 00s & TIME"]
    CheckStartCaptured -->|"บันทึกแล้ว"| RenderHUD
    SaveSafeStart --> RenderHUD
    
    %% ================= สาขา 2: รถสตาร์ทแล้ว / กำลังขับขี่ =================
    CheckEngine -->|"สตาร์ทแล้ว (กำลังขับขี่)"| CheckMidRideHelmet{"ตรวจพบการสวมหมวกต่อเนื่อง?<br/>is_violation == False?"}
    
    CheckMidRideHelmet -->|"สวมหมวกปกติ"| NormalRide["🟢 ขับขี่ปกติ Normal Riding Mode<br/>บิดคันเร่งได้เต็มกำลังปกติ ไม่ตัดความเร็ว<br/>ไฟเขียวติด ไซเรนเงียบ"]
    NormalRide --> RenderHUD
    
    CheckMidRideHelmet -->|"ถอดหมวกกลางคัน"| Stage1_LED["🔴 ขั้นที่ 1: เปิดไฟเตือนสีแดงทันที (LED Red Alert ON)<br/>หน้าจอแสดงข้อความกระพริบเตือนสีแดง"]
    Stage1_LED --> Stage2_Buzzer["🔊 ขั้นที่ 2: ตามด้วยเสียงสัญญาณไซเรนเตือน (Buzzer Alarm Beep)<br/>*(ขับขี่ต่อได้ ไม่ตัดความเร็วกะทันหันเพื่อความปลอดภัย)*"]
    Stage2_Buzzer --> CheckMidRideCooldown{"ครบ Cooldown 4 วิ หรือไม่?"}
    CheckMidRideCooldown -->|"ใช่"| SaveMidRide["📸 บันทึกภาพหลักฐาน mid_ride_*.jpg<br/>ลง captures/mid_ride_violations/ และ all_captures/<br/>ประทับเวลาขับขี่ STOPWATCH: ระยะเวลาขับขี่"]
    CheckMidRideCooldown -->|"ไม่ใช่ หรือ บันทึกแล้ว"| CheckStopStill{"ผู้ขับขี่ชะลอรถจนจอดนิ่ง 0 km/h<br/>แล้วยังไม่สวมหมวกหรือไม่?"}
    SaveMidRide --> CheckStopStill
    
    CheckStopStill -->|"ใช่ (จอดนิ่งสนิท)"| ReLock["ล็อคเครื่องยนต์ใหม่ทันที engine_started = False<br/>ต้องสวมหมวกก่อนจึงจะออกรถได้ใหม่"]
    CheckStopStill -->|"ยังขับขี่อยู่"| RenderHUD
    ReLock --> RenderHUD
    
    %% ================= ส่วนการแสดงผลและลูป =================
    RenderHUD["วาดหน้าจอแสดงผล Dashboard & HUD:<br/>- นาฬิกาเวลาจริง TIME: HH:MM:SS<br/>- ระบบจับเวลาสด STOPWATCH: MM:SS<br/>- กรอบตรวจจับ Bounding Box & ป้ายชื่อ<br/>- แสดงสถานะไฟเตือนและไซเรน"]
    
    RenderHUD --> CheckExit{"ผู้ใช้กดปุ่ม 'q'<br/>เพื่อออกจากโปรแกรมหรือไม่?"}
    CheckExit -->|"ไม่ใช่"| ReadCamera
    CheckExit -->|"ใช่"| End(["🔴 สิ้นสุดการทำงาน ปิดอุปกรณ์"])
```

---

## 2. ผังงานตรรกะการควบคุมและเตือนภัย 2 ระดับ (Two-Stage Safety & Alert Logic)

```mermaid
flowchart LR
    subgraph Part1 ["🔒 จังหวะที่ 1: ก่อนออกรถ (Start Interlock)"]
        P1_Check{"สวมหมวกกันน็อค<br/>ก่อนสตาร์ทหรือไม่?"}
        P1_Check -->|"ไม่สวม"| P1_Lock["⛔ ตัดระบบสตาร์ททันที<br/>บิดคันเร่งไม่ไป<br/>บันทึกภาพ no_helmet"]
        P1_Check -->|"สวมถูกต้อง"| P1_Unlock["✅ ปลดล็อคสตาร์ทรถ<br/>เริ่มจับเวลา Trip Stopwatch<br/>บันทึกภาพ safe_start"]
    end

    subgraph Part2 ["⚠️ จังหวะที่ 2: เมื่อแอบถอดหมวกกลางคัน (Two-Stage Alert)"]
        P1_Unlock --> P2_Ride["ขับขี่บนท้องถนน"]
        P2_Ride --> P2_Check{"ตรวจพบการแอบถอดหมวก<br/>ขณะรถกำลังวิ่งหรือไม่?"}
        P2_Check -->|"สวมหมวกต่อเนื่อง"| P2_Normal["🟢 ขับขี่ปกติเต็มประสิทธิภาพ"]
        P2_Check -->|"ถอดหมวกกลางคัน"| P2_Stage1["🔴 1. เปิดไฟเตือนสีแดงทันที (LED Red ON)"]
        P2_Stage1 --> P2_Stage2["🔊 2. ตามด้วยเสียงไซเรนเตือน (Buzzer Sound)"]
        P2_Stage2 --> P2_Save["📸 3. บันทึกภาพหลักฐาน mid_ride_violation<br/>พร้อมระบุเวลาที่ขับขี่มาแล้ว"]
    end
```

---

## 3. ตารางสถานะการทำงานของระบบ (State Transition Table)

| สถานะของรถ | การตรวจจับหมวก | สวิตช์รีเลย์สตาร์ท | ความเร็วมอเตอร์ | ไฟเตือน LED | เสียงเตือน Buzzer | โฟลเดอร์ที่บันทึกภาพ | ลายน้ำที่ประทับลงภาพ (Watermark) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **ก่อนสตาร์ท / จอดนิ่ง** | ❌ ไม่สวม | **LOCKED (ตัดไฟสตาร์ท)** | บิดไม่ไป (0 km/h) | 🔴 ไฟแดงติด | เงียบ | `captures/no_helmet/` | `[ALERT] NO HELMET DETECTED | STOPWATCH: 00m 25s | ENGINE LOCKED` |
| **ก่อนสตาร์ท / จอดนิ่ง** | ✅ สวมถูกต้อง | **UNLOCKED (พร้อมขับ)** | พร้อมบิดคันเร่ง | 🟢 ไฟเขียวติด | เงียบ | `captures/safe_start/` | `[PASS] SAFE START | HELMET VERIFIED | STOPWATCH: 00m 00s` |
| **กำลังขับขี่บนถนน** | ✅ สวมต่อเนื่อง | **UNLOCKED** | วิ่งความเร็วปกติ | 🟢 ไฟเขียวติด | เงียบ | *(ไม่บันทึกซ้ำ)* | *(ขับขี่ความเร็วปกติ)* |
| **กำลังขับขี่บนถนน** | ❌ แอบถอดกลางคัน | **UNLOCKED** | **ไม่ตัดความเร็ว (วิ่งต่อได้)** | **🔴 1. ไฟแดงเตือนขึ้นก่อน** | **🔊 2. ตามด้วยเสียงเตือนดัง** | `captures/mid_ride_violations/` | `[ALERT] MID-RIDE HELMET REMOVAL | STOPWATCH: 02m 15s | TIME: ...` |
| **ทุกสภาวะ** | กดปุ่ม `[S]` | ตามสภาวะขณะนั้น | ตามสภาวะขณะนั้น | ตามสภาวะ | เงียบ | `captures/manual_snapshots/` | `MANUAL SNAPSHOT | {STATUS} | STOPWATCH: {TIME}` |

> 💡 **หมายเหตุ**: ทุกภาพที่บันทึกจะถูกทำสำเนาส่งไปยังโฟลเดอร์รวม `captures/all_captures/` โดยอัตโนมัติ เพื่อให้เปิดดูภาพทั้งหมดได้ในที่เดียว

---

## 4. คำอธิบายขั้นตอนการทำงานอย่างละเอียด (สำหรับใส่เล่มรายงาน บทที่ 3)

### ขั้นตอนที่ 1: การเริ่มต้นระบบ (System Initialization)
เมื่อเปิดสวิตช์กุญแจรถมอเตอร์ไซค์ไฟฟ้า บอร์ดประมวลผล (Raspberry Pi 4) จะโหลดโมเดลปัญญาประดิษฐ์ YOLOv8n, เปิดกล้องดิจิทัลตรวจจับผู้ขับขี่, และสร้างโครงสร้างโฟลเดอร์จัดเก็บภาพหลักฐาน โดยระบบจะตั้งค่าเริ่มต้นให้ **"ระบบสตาร์ทเครื่องยนต์ถูกล็อค (Engine Locked)"** เสมอเพื่อความปลอดภัย

### ขั้นตอนที่ 2: การประมวลผลภาพจากกล้อง (AI Vision Processing)
กล้องจะจับภาพผู้ขับขี่อย่างต่อเนื่องและส่งเข้าสู่โมเดลตรวจจับวัตถุ เพื่อระบุตำแหน่งบุคคล (Person) และตรวจสอบสภาวะของศีรษะว่าสวมหมวกนิรภัย (Helmet) หรือไม่สวมหมวก (No Helmet) โดยใช้ **7-Frame Majority Filter** ร่วมกับ **สัดส่วนกายวิภาคศีรษะมนุษย์ (Human Anatomical Ratio)** เพื่อให้กรอบตรวจจับนิ่งเสถียร ไม่กะพริบวูบวาบ

### ขั้นตอนที่ 3: การบังคับสวมหมวกก่อนออกรถ (Start Interlock)
- หากผู้ขับขี่ **ไม่สวมหมวกนิรภัย**: สวิตช์รีเลย์จะตัดวงจรสตาร์ทคันเร่ง บิดไม่ไป รถไม่สามารถออกตัวได้ พร้อมบันทึกภาพถ่ายหลักฐาน `no_helmet_*.jpg`
- หากผู้ขับขี่ **สวมหมวกนิรภัยถูกต้อง**: ระบบจะปลดล็อคให้สตาร์ทรถได้ทันที (ENGINE READY), เปิดไฟเขียวแสดงความปลอดภัย, บันทึกภาพยืนยัน `start_verified_*.jpg` และเริ่มนับเวลาการขับขี่ (Live Trip Stopwatch)

### ขั้นตอนที่ 4: การแจ้งเตือนเมื่อแอบถอดหมวกกลางคัน (Two-Stage Mid-Ride Warning Alert)
ขณะที่รถกำลังวิ่งบนท้องถนน หากผู้ขับขี่แอบถอดหมวกนิรภัยกลางคัน ระบบจะ **ไม่ตัดความเร็วกะทันหัน** เพื่อป้องกันอันตรายจากการเสียหลักหรือการถูกชนท้าย แต่จะใช้ **ระบบเตือนภัย 2 จังหวะ**:
1. **จังหวะที่ 1 (เตือนด้วยสายตา)**: แสดงไฟเตือนสีแดง (LED Red Alert) สว่างขึ้นทันที พร้อมหน้าจอกะพริบแจ้งเตือนสีแดง
2. **จังหวะที่ 2 (เตือนด้วยเสียง)**: ตามด้วยเสียงสัญญาณไซเรนเตือน (Buzzer Alarm Beep) ส่งเสียงเตือนต่อเนื่องให้ผู้ขับขี่รู้ตัวและนำหมวกกลับมาสวมใส่
3. **การบันทึกหลักฐาน**: ระบบบันทึกภาพถ่ายหลักฐาน `mid_ride_*.jpg` พร้อมประทับเวลาที่ขับขี่มาแล้ว (Trip Stopwatch) เพื่อเป็นหลักฐานว่ามีการถอดหมวกหลังจากขับขี่ไปนานเท่าใด
4. **เมื่อรถจอดนิ่งสนิท**: หากผู้ขับขี่หยุดรถแล้วยังไม่สวมหมวก ระบบจะทำการล็อคระบบสตาร์ทใหม่อีกครั้งทันที
