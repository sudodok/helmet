"""
=============================================================================
ระบบจำลองตรวจจับหมวกกันน็อคสำหรับรถมอเตอร์ไซค์ไฟฟ้า (PC / Laptop Demo Version)
Helmet Detection System - PC Simulation & Demonstration
=============================================================================
เวอร์ชันสำหรับการนำเสนอและทดสอบบนคอมพิวเตอร์ (Windows / Mac / Linux):
- หน้าปัดรถมอเตอร์ไซค์ไฟฟ้าเสมือนจริง (EV Motorcycle HUD Dashboard)
- จำลองระบบคันเร่งและความเร็ว (Speed & Throttle Physics)
- จำลองการตัดความเร็วอัตโนมัติ 25 km/h เมื่อไม่สวมหมวก (Speed Limiter Relay)
- จำลองสัญญาณเสียง Buzzer (เตือนจริงผ่านลำโพงคอมพิวเตอร์) และไฟ LED เสมือน
- จำลองการรับสัญญาณพิกัดดาวเทียม GPS ATGM336H พร้อมการเคลื่อนที่จริง
- ประทับลายน้ำพิกัด GPS บนภาพหลักฐานลงโฟลเดอร์ captures/
- ปุ่มคีย์ลัดสำหรับสาธิตให้ครูดูได้ทันที แม้ไม่มีหมวกกันน็อคจริง
=============================================================================
"""

import cv2
import numpy as np
import time
import os
import json
import threading
from datetime import datetime

# รองรับเสียงเตือนบน Windows
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


class PCHelmetSimulator:
    def __init__(self):
        # 1. การตั้งค่าโฟลเดอร์
        os.makedirs('captures', exist_ok=True)
        os.makedirs('logs', exist_ok=True)

        # 2. ระบบฟิสิกส์และความเร็วรถมอเตอร์ไซค์ไฟฟ้า
        self.current_speed = 0.0          # ความเร็วปัจจุบัน (km/h)
        self.target_speed = 45.0          # ความเร็วเป้าหมายเมื่อบิดคันเร่ง
        self.speed_limit_violation = 25.0  # ขีดจำกัดความเร็วเมื่อไม่สวมหมวก (km/h)
        self.is_throttling = False        # สถานะการบิดคันเร่ง (เริ่มต้นไม่บิด)
        self.battery_percent = 88         # ระดับแบตเตอรี่รถไฟฟ้า 72V
        self.battery_voltage = 71.4

        # ระบบตัดสตาร์ท (Ignition Start Interlock)
        # ถ้าไม่สวมหมวกตั้งแต่แรก สตาร์ทรถไม่ติด บิดคันเร่งไม่ไป
        self.engine_started = False       # สตาร์ทรถติดแล้วหรือไม่
        self.engine_locked = True         # ล็อคการสตาร์ทเมื่อไม่สวมหมวก

        # 3. สถานะฮาร์ดแวร์จำลอง (Virtual Hardware)
        self.virtual_relay_active = False  # สวิตช์รีเลย์จำกัดความเร็ว
        self.virtual_buzzer_active = False # เสียงเตือน
        self.virtual_led_green = True     # ไฟเขียว (ปลอดภัย)
        self.virtual_led_red = False      # ไฟแดง (อันตราย)

        # 4. สถานะ GPS ATGM336H เสมือนจริง
        self.gps_lat = 13.756331          # พิกัดจำลอง (กรุงเทพฯ)
        self.gps_lon = 100.501765
        self.gps_satellites = 9
        self.gps_fix = True

        # 5. การตรวจจับและโหมดสาธิต (Demo Controls)
        self.manual_override = False      # โหมดควบคุมเองสำหรับสาธิต
        self.forced_helmet_state = False  # บังคับสถานะหมวก (True=สวม, False=ไม่สวม)
        self.camera_source = 0            # กล้องหลัก
        self.use_synthetic_frame = False  # โหมดภาพจำลองถ้าไม่มีกล้อง
        
        # โหลด Haar Cascade สำหรับตรวจจับใบหน้าในโหมดทดสอบ
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        # สถิติ
        self.frame_count = 0
        self.start_time = time.time()
        self.violations_log = []
        self.last_violation_time = 0
        self.violation_cooldown = 4.0     # วินาที
        self.is_violation_active = False

        # เริ่มต้นกล้อง
        self.cap = None
        self._init_camera()

        # เริ่มต้นส่งข้อมูล Telemetry ไปยัง WebApp Server (ทำงานแบบ Background Thread)
        self._init_telemetry()

    def _init_telemetry(self):
        """เริ่มเธรดส่งข้อมูลพิกัดและความเร็วไปยัง WebApp Server (localhost:5000) แบบ Real-time"""
        def telemetry_worker():
            import urllib.request
            while True:
                time.sleep(0.3)
                try:
                    payload = json.dumps({
                        'lat': self.gps_lat,
                        'lon': self.gps_lon,
                        'speed': self.current_speed,
                        'helmet': not (self.is_violation_active or self.engine_locked),
                        'engine_locked': self.engine_locked,
                        'satellites': self.gps_satellites,
                        'source': 'PC Demo Simulator'
                    }).encode('utf-8')
                    req = urllib.request.Request(
                        'http://localhost:5000/api/telemetry',
                        data=payload,
                        headers={'Content-Type': 'application/json'},
                        method='POST'
                    )
                    with urllib.request.urlopen(req, timeout=0.2):
                        pass
                except Exception:
                    pass
        threading.Thread(target=telemetry_worker, daemon=True).start()

    def _init_camera(self):
        """เริ่มต้นเปิดกล้อง Webcam"""
        try:
            self.cap = cv2.VideoCapture(self.camera_source)
            if not self.cap.isOpened():
                print("[WARNING] ไม่สามารถเปิดกล้อง Webcam ได้ - สลับเป็นโหมดจำลองภาพ")
                self.use_synthetic_frame = True
            else:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                print("[INFO] เปิดกล้อง Webcam สำเร็จ")
        except Exception as e:
            print(f"[WARNING] กล้องขัดข้อง: {e} - ใช้โหมดจำลองภาพ")
            self.use_synthetic_frame = True

    def _play_buzzer_sound(self):
        """ส่งเสียงเตือนผ่านลำโพง (ทำงานแยกเธรดเพื่อไม่ให้ภาพกระตุก)"""
        if HAS_WINSOUND:
            def beep_worker():
                try:
                    winsound.Beep(1400, 150)
                except Exception:
                    pass
            threading.Thread(target=beep_worker, daemon=True).start()

    def get_frame(self):
        """ดึงภาพจากกล้องจริง หรือสร้างภาพจำลองผู้ขับขี่"""
        if not self.use_synthetic_frame and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # กลับด้านภาพเหมือนกระจกเงา (Mirror View)
                return cv2.flip(frame, 1)
        
        # ถ้าไม่มีกล้อง สร้างภาพจำลองแบบ High-Tech Studio
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        # พื้นหลังไล่เฉดสี
        for y in range(720):
            frame[y, :] = (int(25 + y * 0.05), int(20 + y * 0.03), int(30 + y * 0.08))

        # วาดรูปจำลองศีรษะผู้ขับขี่
        cx, cy = 640, 380
        if self.forced_helmet_state:
            # วาดหมวกกันน็อคแบบเต็มใบ (สีเขียว/น้ำเงิน)
            cv2.ellipse(frame, (cx, cy - 40), (140, 170), 0, 0, 360, (50, 180, 50), -1)
            cv2.ellipse(frame, (cx, cy - 20), (110, 60), 0, 0, 360, (20, 20, 20), -1)  # ชิลด์หน้า
            cv2.putText(frame, "SIMULATED: HELMET WORN", (cx - 150, cy + 200),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            # วาดศีรษะคนปกติ (ไม่สวมหมวก)
            cv2.ellipse(frame, (cx, cy - 30), (100, 130), 0, 0, 360, (180, 190, 230), -1)
            cv2.circle(frame, (cx - 35, cy - 30), 10, (50, 50, 50), -1) # ตาซ้าย
            cv2.circle(frame, (cx + 35, cy - 30), 10, (50, 50, 50), -1) # ตาขวา
            cv2.putText(frame, "SIMULATED: NO HELMET", (cx - 140, cy + 200),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return frame

    def analyze_frame(self, frame):
        """วิเคราะห์ภาพว่าสวมหมวกหรือไม่"""
        # 1. หากเปิด Manual Override ใช้ค่าที่กำหนดโดยตรง (สะดวกในการพรีเซนต์)
        if self.manual_override:
            has_helmet = self.forced_helmet_state
            detections = [{
                'class': 'helmet' if has_helmet else 'no_helmet',
                'confidence': 0.96,
                'box': [490, 200, 300, 350]
            }]
            return detections, not has_helmet

        # 2. ตรวจจับอัตโนมัติผ่าน Haar Cascade
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.2, minNeighbors=5, minSize=(90, 90)
        )

        detections = []
        violation = False

        if len(faces) == 0:
            # หากตรวจไม่พบใบหน้า ให้ถือว่าปลอดภัยหรือสวมหมวกปิดหน้า
            detections.append({'class': 'helmet', 'confidence': 0.85, 'box': [500, 200, 280, 320]})
            violation = False
        else:
            for (x, y, w, h) in faces:
                # วิเคราะห์บริเวณเหนือศีรษะ (Headwear region)
                roi_y = max(0, y - int(h * 0.75))
                head_roi = gray[roi_y:y, x:x+w]

                has_helmet = False
                if head_roi.size > 0:
                    edges = cv2.Canny(head_roi, 60, 160)
                    edge_density = np.sum(edges > 0) / head_roi.size
                    std_dev = np.std(head_roi)
                    # หมวกกันน็อคมักมีขอบโค้งหนาแน่นและสีเรียบ/สะท้อนแสง
                    if edge_density > 0.12 or std_dev < 35:
                        has_helmet = True

                if has_helmet:
                    detections.append({'class': 'helmet', 'confidence': 0.90, 'box': [x, roi_y, w, y - roi_y + h]})
                else:
                    detections.append({'class': 'no_helmet', 'confidence': 0.92, 'box': [x, y, w, h]})
                    violation = True

        return detections, violation

    def update_physics(self, is_violation):
        """จำลองระบบขับเคลื่อนรถมอเตอร์ไซค์ไฟฟ้าจริง พร้อมระบบตัดสตาร์ท (Start Interlock)"""
        self.is_violation_active = is_violation
        # 1. กรณีที่รถยังไม่สตาร์ท หรือรถจอดนิ่ง:
        if not self.engine_started or self.current_speed == 0.0:
            if is_violation:
                # ไม่สวมหมวกตั้งแต่แรก -> สตาร์ทรถไม่ติดเด็ดขาด!
                self.engine_started = False
                self.engine_locked = True
                self.current_speed = 0.0
                self.is_throttling = False
                self.virtual_relay_active = True   # รีเลย์ตัดวงจรสตาร์ท/คันเร่ง
                self.virtual_led_green = False
                self.virtual_led_red = True
                self.virtual_buzzer_active = True
                return
            else:
                # ตรวจพบการสวมหมวก -> สตาร์ทเครื่องติด พร้อมขับขี่ (READY)
                if self.engine_locked:
                    print("[IGNITION] ✅ ตรวจพบหมวกนิรภัย: ปลดล็อคระบบสตาร์ทสำเร็จ (ENGINE READY)")
                self.engine_started = True
                self.engine_locked = False
                self.virtual_relay_active = False
                self.virtual_led_green = True
                self.virtual_led_red = False
                self.virtual_buzzer_active = False

        # 2. กรณีที่รถสตาร์ทติดแล้ว และกำลังขับขี่อยู่:
        if is_violation:
            self.virtual_relay_active = True   # สั่ง Relay ล็อคความเร็ว
            self.virtual_led_green = False
            self.virtual_led_red = True
            self.virtual_buzzer_active = True
            
            # ลดความเร็วลงสู่ขีดจำกัด 25 km/h ทันที (จำลองการตัดแรงดันคันเร่ง)
            if self.current_speed > self.speed_limit_violation:
                self.current_speed -= 1.8  # เบรกหน่วงอัตโนมัติ
                if self.current_speed < self.speed_limit_violation:
                    self.current_speed = self.speed_limit_violation
            elif self.is_throttling and self.current_speed < self.speed_limit_violation:
                self.current_speed = min(self.speed_limit_violation, self.current_speed + 0.5)
            
            # ถ้ารถจอดนิ่งสนิท แล้วยังไม่ใส่หมวก -> ล็อคสตาร์ทใหม่ทันที!
            if self.current_speed <= 0.2 and not self.is_throttling:
                self.engine_started = False
                self.engine_locked = True
        else:
            self.virtual_relay_active = False  # ปลดล็อคความเร็ว
            self.virtual_led_green = True
            self.virtual_led_red = False
            self.virtual_buzzer_active = False

            # วิ่งสู่ความเร็วปกติที่ผู้ขับขี่บิดคันเร่ง
            if self.is_throttling:
                if self.current_speed < self.target_speed:
                    self.current_speed += 0.8
                elif self.current_speed > self.target_speed:
                    self.current_speed -= 0.5
            else:
                self.current_speed = max(0.0, self.current_speed - 0.4)

        # จำลองการเคลื่อนที่ของ GPS ตามความเร็วจริง
        speed_deg_factor = (self.current_speed / 3600.0) * 0.009
        self.gps_lat += speed_deg_factor * 0.04
        self.gps_lon += speed_deg_factor * 0.08

    def process_violation(self, frame, detections):
        """บันทึกข้อมูลและภาพถ่ายหลักฐานการละเมิดพร้อมลายน้ำพิกัด"""
        now = time.time()
        if now - self.last_violation_time < self.violation_cooldown:
            return

        self.last_violation_time = now
        timestamp = datetime.now()

        # สร้างภาพถ่ายหลักฐานพร้อมแถบลายน้ำพิกัด GPS
        evidence_frame = frame.copy()
        h, w = evidence_frame.shape[:2]
        
        # วาดแถบดำคาดด้านล่างสำหรับลายน้ำ
        cv2.rectangle(evidence_frame, (0, h - 48), (w, h), (15, 15, 15), -1)
        cv2.rectangle(evidence_frame, (0, h - 48), (w, h - 46), (0, 0, 255), -1)

        watermark_text = (
            f"EV-ALERT | NO HELMET | SPEED: {self.current_speed:.1f} KM/H | "
            f"GPS: {self.gps_lat:.6f} N, {self.gps_lon:.6f} E | "
            f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        cv2.putText(evidence_frame, watermark_text, (16, h - 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 1)

        filename = f"captures/violation_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(filename, evidence_frame)

        # บันทึก JSON Log
        violation_data = {
            'timestamp': timestamp.isoformat(),
            'speed_kmh': round(self.current_speed, 1),
            'gps': {
                'latitude': round(self.gps_lat, 6),
                'longitude': round(self.gps_lon, 6),
                'satellites': self.gps_satellites,
                'module': 'ATGM336H / NEO-M8N'
            },
            'relay_state': 'ACTIVE_LIMIT_25KMH',
            'image_file': filename
        }
        self.violations_log.append(violation_data)

        # เขียนลงไฟล์รายวัน
        log_file = f"logs/violations_{timestamp.strftime('%Y%m%d')}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self.violations_log, f, indent=2, ensure_ascii=False)

        # เล่นเสียงเตือน
        self._play_buzzer_sound()
        print(f"[ALERT] ตรวจพบไม่สวมหมวก! บันทึกภาพ: {filename} | พิกัด GPS: {self.gps_lat:.5f}, {self.gps_lon:.5f}")

    def draw_hud(self, frame, detections, violation):
        """วาดหน้าปัดและแดชบอร์ดรถมอเตอร์ไซค์ไฟฟ้าเสมือนจริง (EV Motorcycle HUD)"""
        h, w = frame.shape[:2]

        # 1. วาดกรอบตรวจจับ (Bounding Boxes)
        for det in detections:
            cls = det['class']
            conf = det['confidence']
            bx, by, bw, bh = det['box']
            color = (0, 230, 0) if cls == 'helmet' else (0, 0, 255)

            cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), color, 3)
            label = f"{'HELMET OK' if cls == 'helmet' else 'NO HELMET'} ({int(conf*100)}%)"
            
            # ป้ายชื่อหัวมุม
            cv2.rectangle(frame, (bx, by - 32), (bx + len(label)*11 + 10, by), color, -1)
            cv2.putText(frame, label, (bx + 6, by - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        # 2. แถบสถานะด้านบน (Top Status Bar)
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 55), (15, 15, 20), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        # หัวข้อระบบ
        cv2.putText(frame, "E-MOTORCYCLE SMART HELMET INTERLOCK SYSTEM", (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

        # สถานะแบตเตอรี่รถไฟฟ้า
        bat_color = (0, 255, 0) if self.battery_percent > 30 else (0, 0, 255)
        cv2.putText(frame, f"BAT: {self.battery_voltage:.1f}V ({self.battery_percent}%)", (w - 480, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, bat_color, 2)

        # สถานะ GPS
        cv2.putText(frame, f"GPS ATGM336H: 3D FIX ({self.gps_satellites} Sats)", (w - 270, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (100, 240, 255), 2)

        # 3. กล่องควบคุมฮาร์ดแวร์เสมือนจริง (Virtual Hardware Panel - ด้านขวา)
        rh_x = w - 340
        overlay2 = frame.copy()
        cv2.rectangle(overlay2, (rh_x, 70), (w - 15, 340), (10, 12, 18), -1)
        cv2.addWeighted(overlay2, 0.82, frame, 0.18, 0, frame)
        cv2.rectangle(frame, (rh_x, 70), (w - 15, 340), (70, 80, 95), 1)

        cv2.putText(frame, "HARDWARE INTERFACE (RPI 4)", (rh_x + 15, 96),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 220, 255), 2)
        cv2.line(frame, (rh_x + 15, 105), (w - 30, 105), (100, 120, 140), 1)

        # ไฟ LED เขียว / แดง
        led_g_color = (0, 255, 0) if self.virtual_led_green else (40, 70, 40)
        led_r_color = (0, 0, 255) if self.virtual_led_red else (70, 40, 40)
        cv2.circle(frame, (rh_x + 30, 130), 8, led_g_color, -1)
        cv2.putText(frame, f"LED GREEN (SAFE): {'ON' if self.virtual_led_green else 'OFF'}", (rh_x + 48, 135),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (220, 220, 220), 1)

        cv2.circle(frame, (rh_x + 30, 160), 8, led_r_color, -1)
        cv2.putText(frame, f"LED RED (ALERT): {'ON' if self.virtual_led_red else 'OFF'}", (rh_x + 48, 165),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (220, 220, 220), 1)

        # รีเลย์ตัดความเร็วและระบบตัดสตาร์ท
        if self.engine_locked:
            relay_text = "LOCKED (START OFF)"
            relay_col = (0, 0, 255)
        elif self.virtual_relay_active:
            relay_text = "LIMIT 25 KM/H"
            relay_col = (0, 150, 255)
        else:
            relay_text = "NORMAL (UNLOCKED)"
            relay_col = (0, 255, 0)
        cv2.putText(frame, f"INTERLOCK: {relay_text}", (rh_x + 18, 198),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, relay_col, 2)

        # สัญญาณ Buzzer
        buzzer_text = "ACTIVE (BEEPING)" if self.virtual_buzzer_active else "SILENT"
        buzzer_col = (0, 0, 255) if self.virtual_buzzer_active else (180, 180, 180)
        cv2.putText(frame, f"BUZZER 5V: {buzzer_text}", (rh_x + 18, 228),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, buzzer_col, 1)

        # สถิติ
        cv2.putText(frame, f"Total Frames: {self.frame_count}", (rh_x + 18, 260),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (200, 200, 200), 1)
        cv2.putText(frame, f"Total Violations: {len(self.violations_log)}", (rh_x + 18, 285),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 180, 255), 2)
        cv2.putText(frame, f"Demo Mode: {'MANUAL (H key)' if self.manual_override else 'AUTO CAMERA'}", (rh_x + 18, 312),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (150, 255, 180), 1)

        # 4. หน้าปัดเรือนไมล์รถมอเตอร์ไซค์ไฟฟ้า (Digital Speedometer Dashboard - ด้านซ้ายล่าง)
        dash_w, dash_h = 320, 180
        overlay3 = frame.copy()
        cv2.rectangle(overlay3, (20, h - dash_h - 60), (20 + dash_w, h - 60), (12, 14, 20), -1)
        cv2.addWeighted(overlay3, 0.85, frame, 0.15, 0, frame)
        cv2.rectangle(frame, (20, h - dash_h - 60), (20 + dash_w, h - 60), (60, 70, 90), 1)

        # ตัวเลขความเร็วใหญ่
        if self.engine_locked:
            cv2.putText(frame, "LOCK", (38, h - 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 4)
            cv2.putText(frame, "(0 km/h)", (195, h - 135),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (160, 160, 160), 2)
            speed_color = (0, 0, 255)
        else:
            speed_color = (0, 255, 0) if not self.virtual_relay_active else (0, 150, 255)
            if self.current_speed > 60:
                speed_color = (0, 0, 255)

            cv2.putText(frame, f"{self.current_speed:.0f}", (55, h - 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.5, speed_color, 4)
            cv2.putText(frame, "km/h", (165, h - 135),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 200, 200), 2)

        # แถบวัดระดับความเร็ว (Speed Bar)
        bar_x, bar_y, bar_w, bar_h = 40, h - 105, 270, 14
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 60), -1)
        fill_w = int((self.current_speed / 80.0) * bar_w) if not self.engine_locked else 0
        fill_w = max(0, min(bar_w, fill_w))
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), speed_color, -1)

        # ข้อความสถานะคันเร่ง / สตาร์ท
        if self.engine_locked:
            throttle_status = "ENGINE: LOCKED (NO HELMET)"
            t_col = (0, 0, 255)
        else:
            throttle_status = "THROTTLE: APPLIED" if self.is_throttling else "THROTTLE: RELEASED"
            t_col = (0, 255, 0) if self.is_throttling else (180, 200, 220)
        cv2.putText(frame, throttle_status, (40, h - 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, t_col, 1)

        # 5. ป้ายเตือนกระพริบกลางจอ
        if self.engine_locked:
            # แจ้งเตือนตัดสตาร์ทเครื่องยนต์ตัวโตๆ
            alert_box_w, alert_box_h = 630, 75
            ab_x = (w - alert_box_w) // 2
            ab_y = h - 150
            cv2.rectangle(frame, (ab_x, ab_y), (ab_x + alert_box_w, ab_y + alert_box_h), (0, 0, 190), -1)
            cv2.rectangle(frame, (ab_x - 3, ab_y - 3), (ab_x + alert_box_w + 3, ab_y + alert_box_h + 3), (0, 255, 255), 2)
            cv2.putText(frame, "⛔ ENGINE START LOCKED: NO HELMET !", (ab_x + 20, ab_y + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2)
            cv2.putText(frame, "MOTORCYCLE CANNOT START. WEAR HELMET FIRST (Press H)", (ab_x + 22, ab_y + 58),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 255), 2)
        elif violation:
            if int(time.time() * 3) % 2 == 0:
                alert_box_w, alert_box_h = 580, 65
                ab_x = (w - alert_box_w) // 2
                ab_y = h - 145
                cv2.rectangle(frame, (ab_x, ab_y), (ab_x + alert_box_w, ab_y + alert_box_h), (0, 0, 220), -1)
                cv2.rectangle(frame, (ab_x - 3, ab_y - 3), (ab_x + alert_box_w + 3, ab_y + alert_box_h + 3), (0, 255, 255), 2)
                cv2.putText(frame, "! WARNING: NO HELMET DETECTED !", (ab_x + 35, ab_y + 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
                cv2.putText(frame, "MOTOR SPEED RESTRICTED TO MAX 25 KM/H", (ab_x + 55, ab_y + 52),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 0), 2)

        # 6. แถบล่างสุด: พิกัด GPS แบบ Real-time และแถบวิธีใช้งาน
        overlay4 = frame.copy()
        cv2.rectangle(overlay4, (0, h - 50), (w, h), (10, 10, 15), -1)
        cv2.addWeighted(overlay4, 0.9, frame, 0.1, 0, frame)

        gps_info = f"GPS POS: {self.gps_lat:.6f} N, {self.gps_lon:.6f} E | SATS: {self.gps_satellites} | SPEED: {self.current_speed:.1f} KM/H"
        cv2.putText(frame, gps_info, (20, h - 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        shortcuts = "[H] Toggle Helmet | [T/Up] Throttle | [B/Down] Brake | [S] Capture | [R] Reset | [Q] Quit"
        cv2.putText(frame, shortcuts, (20, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 190, 200), 1)

        return frame

    def run(self):
        """ลูปการทำงานหลักของโปรแกรมจำลอง"""
        print("=" * 65)
        print(" 🛵 ระบบจำลองตรวจจับหมวกกันน็อครถมอเตอร์ไซค์ไฟฟ้า (PC Demo Version)")
        print("=" * 65)
        print(" คีย์ลัดสำหรับการสาธิต (Key Controls):")
        print("   [H] : สลับสถานะ สวมหมวก / ไม่สวมหมวก (Force Helmet Toggle)")
        print("   [T] หรือ [Up]   : บิดคันเร่ง (เพิ่มความเร็ว)")
        print("   [B] หรือ [Down] : แตะเบรก (ลดความเร็ว)")
        print("   [S] : บันทึกภาพถ่ายหลักฐานพร้อมลายน้ำพิกัด GPS ทันที")
        print("   [R] : รีเซ็ตสถิติและการละเมิด")
        print("   [M] : สลับโหมดกล้องจริง / โหมดภาพจำลอง (Camera / Synthetic)")
        print("   [Q] : ออกจากโปรแกรม")
        print("=" * 65)

        window_name = "E-Motorcycle Helmet Detection Simulator (PC Demo)"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)

        try:
            while True:
                self.frame_count += 1
                
                # 1. ดึงภาพ
                frame = self.get_frame()
                
                # 2. วิเคราะห์หมวกนิรภัย
                detections, violation = self.analyze_frame(frame)
                
                # 3. คำนวณฟิสิกส์ความเร็วและ GPS
                self.update_physics(violation)
                
                # 4. หากพบการละเมิด บันทึกภาพและประทับลายน้ำพิกัด
                if violation:
                    self.process_violation(frame, detections)
                
                # 5. วาดแดชบอร์ด HUD
                frame = self.draw_hud(frame, detections, violation)
                
                # 6. แสดงผลหน้าต่าง
                cv2.imshow(window_name, frame)

                # ตรวจจับการกดปุ่มกากบาท [X] ปิดหน้าต่าง (ป้องกันหน้าต่างค้าง Not Responding บน Windows)
                try:
                    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                        break
                except Exception:
                    pass
                
                # 7. จัดการคีย์บอร์ด
                key = cv2.waitKey(20) & 0xFF
                if key == ord('q') or key == 27:  # Q หรือ Esc
                    break
                elif key == ord('h') or key == ord('H'):
                    self.manual_override = True
                    self.forced_helmet_state = not self.forced_helmet_state
                    status_str = "สวมหมวกนิรภัย (HELMET ON)" if self.forced_helmet_state else "ไม่สวมหมวกนิรภัย (NO HELMET)"
                    print(f"[DEMO CONTROL] บังคับสถานะ: {status_str}")
                elif key == ord('t') or key == ord('T') or key == 82: # T หรือ Up Arrow
                    if self.engine_locked:
                        print("[LOCKED] ⛔ สตาร์ทรถไม่ติด! มอเตอร์ไม่ทำงาน กรุณาสวมหมวกนิรภัยก่อน (กด 'H' เพื่อจำลองสวมหมวก)")
                        self._play_buzzer_sound()
                    else:
                        self.is_throttling = True
                        self.target_speed = min(75.0, self.target_speed + 5.0)
                        print(f"[THROTTLE] เร่งความเร็วเป้าหมาย: {self.target_speed:.0f} km/h")
                elif key == ord('b') or key == ord('B') or key == 84: # B หรือ Down Arrow
                    self.target_speed = max(0.0, self.target_speed - 10.0)
                    if self.target_speed == 0:
                        self.is_throttling = False
                    print(f"[BRAKE] ลดความเร็วเป้าหมาย: {self.target_speed:.0f} km/h")
                elif key == ord('s') or key == ord('S'):
                    self.last_violation_time = 0
                    self.process_violation(frame, detections)
                elif key == ord('r') or key == ord('R'):
                    self.violations_log.clear()
                    self.current_speed = 0.0
                    self.target_speed = 45.0
                    self.manual_override = False
                    print("[RESET] รีเซ็ตสถิติทั้งหมดเรียบร้อย")
                elif key == ord('m') or key == ord('M'):
                    self.use_synthetic_frame = not self.use_synthetic_frame
                    print(f"[MODE] สลับเป็นโหมด: {'ภาพจำลอง (Synthetic)' if self.use_synthetic_frame else 'กล้องเว็บแคมจริง'}")

        except KeyboardInterrupt:
            print("\n[INFO] หยุดการทำงาน...")
        finally:
            if self.cap and self.cap.isOpened():
                self.cap.release()
            cv2.destroyAllWindows()
            for _ in range(5):
                cv2.waitKey(1)  # Flush Windows message queue ป้องกันหน้าต่างค้าง
            self._print_summary()

    def _print_summary(self):
        """สรุปรายงานหลังปิดโปรแกรม"""
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0
        print("\n" + "=" * 65)
        print(" 📊 สรุปผลการทดสอบระบบจำลอง (Simulation Report)")
        print("=" * 65)
        print(f" จำนวนเฟรมประมวลผล : {self.frame_count} เฟรม")
        print(f" เวลาทำงานทั้งหมด    : {elapsed:.1f} วินาที (FPS: {fps:.1f})")
        print(f" ตรวจพบการละเมิด    : {len(self.violations_log)} ครั้ง")
        print(f" พิกัด GPS ล่าสุด   : Lat {self.gps_lat:.6f}, Lon {self.gps_lon:.6f}")
        print(f" โฟลเดอร์ภาพหลักฐาน : captures/")
        print("=" * 65)


if __name__ == '__main__':
    simulator = PCHelmetSimulator()
    simulator.run()
