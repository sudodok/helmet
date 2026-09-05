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
from collections import deque

# รองรับเสียงเตือนบน Windows
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


class PCHelmetSimulator:
    def __init__(self):
        # 1. การตั้งค่าโฟลเดอร์ (Absolute Paths อิงตำแหน่งโปรเจกต์เสมอ)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.captures_dir = os.path.join(self.base_dir, 'captures')
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        os.makedirs(self.captures_dir, exist_ok=True)
        os.makedirs(os.path.join(self.captures_dir, 'all_captures'), exist_ok=True) # โฟลเดอร์รวมรูปทุกเหตุการณ์ไว้ที่เดียว ไม่แยกหมวดหมู่
        os.makedirs(os.path.join(self.captures_dir, 'safe_start'), exist_ok=True)
        os.makedirs(os.path.join(self.captures_dir, 'mid_ride_violations'), exist_ok=True)
        os.makedirs(os.path.join(self.captures_dir, 'no_helmet'), exist_ok=True) # โฟลเดอร์ตรวจพบไม่สวมหมวก (ไม่ใช่ถอดกลางคัน)
        os.makedirs(os.path.join(self.captures_dir, 'manual_snapshots'), exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

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
        self.face_cascade_alt = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml')

        # ระบบลดอาการสั่นของกรอบ (Exponential Moving Average Box Smoothing)
        self.prev_person_box = None
        self.prev_head_box = None
        # ระบบกรองการกระพริบของสถานะ (7-Frame Temporal Majority Filter)
        self.status_history = deque(maxlen=7)

        # ระบบตรวจจับการเดินทางและถอดหมวกกลางคัน (Smart Event Capture & Trip Tracking)
        self.trip_start_time = None          # เวลาที่สตาร์ทรถสำเร็จ
        self.has_captured_start = False      # ป้องกันการบันทึกภาพตอนสตาร์ทซ้ำซ้อน
        self.last_known_helmet_state = False # สถานะหมวกในเฟรมก่อนหน้า เพื่อตรวจจับจังหวะ "ถอดหมวก" 

        # โหลดโมเดล YOLOv8 สำหรับตรวจจับบุคคล (Person) และหมวกนิรภัย
        self.yolo_model = None
        try:
            from ultralytics import YOLO
            model_path = os.path.join(os.path.dirname(__file__), 'yolov8n.pt')
            if not os.path.exists(model_path):
                model_path = 'yolov8n.pt'
            if os.path.exists(model_path):
                self.yolo_model = YOLO(model_path)
                print('[INFO] โหลด YOLOv8n สำเร็จ (เปิดใช้งานระบบตรวจจับ Person & Vehicle)')
        except Exception as e:
            print(f'[INFO] ใช้ระบบตรวจจับ Cascade / Fallback: {e}')

        # สถิติ
        self.frame_count = 0
        self.start_time = time.time()
        self.violations_log = []
        self.last_violation_time = 0
        self.violation_cooldown = 4.0     # วินาที
        self.last_no_helmet_time = 0      # เวลาที่บันทึกภาพไม่สวมหมวกครั้งล่าสุด
        self.no_helmet_cooldown = 5.0     # หน่วงเวลาถ่ายภาพไม่สวมหมวกซ้ำ (วินาที)
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
                # กลับด้านภาพเหมือนกระจกเงา (Mirror View) และปรับขนาดให้คงที่ 1280x720 เพื่อความคมชัด
                frame = cv2.flip(frame, 1)
                if frame.shape[1] != 1280 or frame.shape[0] != 720:
                    frame = cv2.resize(frame, (1280, 720))
                return frame
        
        # ถ้าไม่มีกล้อง สร้างภาพจำลองแบบ High-Tech Studio
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        # พื้นหลังไล่เฉดสี
        for y in range(720):
            frame[y, :] = (int(25 + y * 0.05), int(20 + y * 0.03), int(30 + y * 0.08))

        # วาดรูปจำลองตัวคนและศีรษะผู้ขับขี่ (Rider Silhouette)
        cx, cy = 640, 380
        # วาดลำตัวผู้ขับขี่ (Torso & Shoulders)
        cv2.ellipse(frame, (cx, cy + 220), (220, 160), 0, 0, 360, (55, 60, 75), -1)
        cv2.rectangle(frame, (cx - 180, cy + 180), (cx + 180, 720), (45, 50, 65), -1)
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

    def _smooth_box(self, new_box, prev_box, alpha=0.65):
        """ช่วยลดอาการสั่นของกรอบตรวจจับ (Exponential Moving Average Smoothing)"""
        if prev_box is None:
            return new_box
        return [
            int(alpha * n + (1 - alpha) * p)
            for n, p in zip(new_box, prev_box)
        ]

    def analyze_frame(self, frame):
        """วิเคราะห์ภาพตรวจจับคน (Person) และหมวกนิรภัย (Helmet) แบบนิ่ง เสถียร ไม่กระพริบ และติดตามตัวตลอดเวลา"""
        detections = []
        h_frame, w_frame = frame.shape[:2]

        person_box = None
        head_box = None
        has_helmet_detected = False

        # 1. ค้นหาตำแหน่งร่างกายคน (Person Detection)
        if not self.use_synthetic_frame:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # ค้นหาด้วย YOLOv8n
            if self.yolo_model is not None:
                try:
                    results = self.yolo_model(frame, imgsz=480, verbose=False, conf=0.35)[0]
                    best_person_area = 0
                    for box in results.boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        xyxy = box.xyxy[0].cpu().numpy().astype(int)
                        bx, by, bx2, by2 = xyxy
                        bw, bh = max(10, bx2 - bx), max(10, by2 - by)

                        if cls_id == 0:  # Person
                            area = bw * bh
                            if area > best_person_area:
                                best_person_area = area
                                person_box = [max(0, bx), max(0, by), min(w_frame - bx, bw), min(h_frame - by, bh), conf]
                        elif cls_id == 3:  # Motorcycle
                            detections.append({
                                'class': 'motorcycle',
                                'confidence': conf,
                                'box': [bx, by, bw, bh]
                            })
                except Exception:
                    pass

            # 2. ค้นหาตำแหน่งและประเมินหมวกนิรภัย
            if person_box is not None:
                # ปรับกรอบคนให้นุ่มนวล ลดอาการกระตุก (Smooth Person Box)
                raw_p_coords = person_box[:4]
                p_conf = person_box[4]
                smoothed_p = self._smooth_box(raw_p_coords, self.prev_person_box, alpha=0.60)
                self.prev_person_box = smoothed_p
                bx, by, bw, bh = smoothed_p

                # ค้นหาใบหน้าเฉพาะช่วงครึ่งบนของตัวคน (Upper 60% of body)
                upper_h = int(bh * 0.60)
                upper_roi = gray[by:by + upper_h, bx:bx + bw]
                faces = []
                if upper_roi.size > 0:
                    faces = self.face_cascade_alt.detectMultiScale(
                        upper_roi, scaleFactor=1.12, minNeighbors=4, minSize=(50, 50)
                    )
                    if len(faces) == 0:
                        faces = self.face_cascade.detectMultiScale(
                            upper_roi, scaleFactor=1.15, minNeighbors=3, minSize=(50, 50)
                        )

                # กำหนดขนาดศีรษะตามสัดส่วนร่างกายมนุษย์ที่คงที่ (Human Head Proportional Ratio)
                # ศีรษะคนปกติกว้างประมาณ 40-42% ของความกว้างช่วงไหล่ และอัตราส่วน กว้าง:สูง ประมาณ 1:1.18
                prop_w = max(50, int(bw * 0.42))
                prop_h = int(prop_w * 1.18)

                if len(faces) > 0:
                    # พบใบหน้า: ใช้ตำแหน่งใบหน้ากำหนดจุดศูนย์กลางศีรษะ
                    fx, fy, fw, fh = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)[0]
                    center_x = bx + fx + fw // 2
                    center_y = by + fy + int(fh * 0.35)

                    # คำนวณขนาดที่กลมกลืน ไม่ให้กระโดดเล็กใหญ่เกินขนาดสัดส่วนตัว (Blended Head Dimension)
                    face_w = int(fw * 1.45)
                    face_h = int(fh * 1.65)
                    head_w = int(0.55 * face_w + 0.45 * prop_w)
                    head_h = int(0.55 * face_h + 0.45 * prop_h)

                    head_left = max(0, center_x - head_w // 2)
                    head_top = max(0, center_y - int(head_h * 0.55))
                    raw_head = [head_left, head_top, head_w, head_h]

                    # ตรวจสอบเหนือหน้าผากว่ามีหมวกกันน็อคครอบอยู่หรือไม่
                    forehead_top = max(0, by + fy - int(fh * 0.45))
                    forehead_roi = frame[forehead_top:by + fy, bx + fx:bx + fx + fw]
                    if forehead_roi.size > 0:
                        hsv = cv2.cvtColor(forehead_roi, cv2.COLOR_BGR2HSV)
                        is_helmet_material = np.mean(hsv[:, :, 1] > 100) > 0.40 or np.mean(hsv[:, :, 2] > 200) > 0.45
                        has_helmet_detected = is_helmet_material
                    else:
                        has_helmet_detected = False
                else:
                    # ไม่พบใบหน้า: ล็อคขนาดและตำแหน่งให้อยู่ตรงกลางส่วนบนของลำตัวอย่างคงที่และนิ่งสนิท
                    center_x = bx + bw // 2
                    center_y = by + int(prop_h * 0.48)

                    head_w = prop_w
                    head_h = prop_h
                    head_left = max(0, center_x - head_w // 2)
                    head_top = max(0, center_y - int(head_h * 0.55))
                    raw_head = [head_left, head_top, head_w, head_h]

                    # ตรวจสอบว่าศีรษะมีหมวกครอบหรือไม่
                    head_roi = frame[head_top:head_top + head_h, head_left:head_left + head_w]
                    if head_roi.size > 0:
                        hsv = cv2.cvtColor(head_roi, cv2.COLOR_BGR2HSV)
                        if np.mean(hsv[:, :, 1] > 110) > 0.35 or np.mean(hsv[:, :, 2] > 210) > 0.45:
                            has_helmet_detected = True
                        else:
                            has_helmet_detected = False
                    else:
                        has_helmet_detected = False

                # ปรับกรอบศีรษะให้นุ่มนวล (Smooth Head Box)
                smoothed_head = self._smooth_box(raw_head, self.prev_head_box, alpha=0.60)
                self.prev_head_box = smoothed_head
                head_box = smoothed_head
                person_box = [bx, by, bw, bh, p_conf]

        # 3. โหมดภาพจำลอง (Synthetic Mode)
        if person_box is None:
            if self.use_synthetic_frame:
                cx, cy = 640, 380
                person_box = [cx - 220, cy - 140, 440, 520, 0.95]
                head_box = [cx - 130, cy - 110, 260, 240]
                has_helmet_detected = self.forced_helmet_state
            else:
                return detections, False

        # 4. ใส่ผลลัพธ์กรอบคน (PERSON)
        px, py, pw, ph, p_conf = person_box
        detections.append({
            'class': 'person',
            'confidence': float(p_conf),
            'box': [int(px), int(py), int(pw), int(ph)]
        })

        # 5. กรองสถานะหมวกด้วย 7-Frame Majority Filter ป้องกันการกระพริบสลับสี
        if self.manual_override:
            # โหมดจำลอง: ล็อคสถานะตามที่ผู้ใช้กด H
            final_helmet = self.forced_helmet_state
            conf_helmet = 0.97
        else:
            self.status_history.append(has_helmet_detected)
            # ต้องมีคะแนนเสียงเกินครึ่งของ 7 เฟรมล่าสุดถึงจะเปลี่ยนสถานะ
            final_helmet = (sum(self.status_history) / len(self.status_history)) >= 0.5
            conf_helmet = 0.93 if final_helmet else 0.91

        hx, hy, hw, hh = head_box
        detections.append({
            'class': 'helmet' if final_helmet else 'no_helmet',
            'confidence': float(conf_helmet),
            'box': [int(hx), int(hy), int(hw), int(hh)]
        })

        violation = not final_helmet
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
                self.has_captured_start = False    # รีเซ็ตพร้อมถ่ายภาพยืนยันการสตาร์ทครั้งใหม่
                self.trip_start_time = None
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

    def _save_evidence_image(self, frame, detections, filename, watermark_text, banner_color=(0, 0, 255)):
        """วาดกรอบตรวจจับและแถบลายน้ำลงบนภาพ แล้วบันทึกลงโฟลเดอร์ captures/"""
        evidence_frame = frame.copy()
        h, w = evidence_frame.shape[:2]

        # 1. วาดกรอบตรวจจับ (Bounding Boxes: Person, Helmet, Motorcycle)
        for det in detections:
            cls = det['class']
            conf = float(det['confidence'])
            bx, by, bw, bh = [int(v) for v in det['box']]

            if cls == 'helmet':
                color = (0, 230, 0)      # สีเขียวสด
                label = f"HELMET OK ({int(conf*100)}%)"
                text_color = (255, 255, 255)
                box_thickness = 3
            elif cls == 'no_helmet':
                color = (0, 0, 255)      # สีแดงสด
                label = f"NO HELMET VIOLATION ({int(conf*100)}%)"
                text_color = (255, 255, 255)
                box_thickness = 3
            elif cls == 'person':
                color = (255, 215, 0)    # สีเหลืองทอง
                label = f"PERSON ({int(conf*100)}%)"
                text_color = (20, 20, 20)
                box_thickness = 2
            elif cls == 'motorcycle':
                color = (255, 140, 0)    # สีส้ม
                label = f"MOTORCYCLE ({int(conf*100)}%)"
                text_color = (255, 255, 255)
                box_thickness = 2
            else:
                color = (200, 200, 200)
                label = f"{cls.upper()} ({int(conf*100)}%)"
                text_color = (0, 0, 0)
                box_thickness = 2

            cv2.rectangle(evidence_frame, (bx, by), (bx + bw, by + bh), color, box_thickness)

            # ป้ายชื่อหัวมุม
            tw = len(label) * 9 + 10
            lbl_y1 = max(0, by - 26)
            lbl_y2 = max(26, by)
            cv2.rectangle(evidence_frame, (bx, lbl_y1), (bx + tw, lbl_y2), color, -1)
            cv2.putText(evidence_frame, label, (bx + 5, max(18, by - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, text_color, 2)

        # 2. วาดแถบดำคาดด้านล่างสำหรับลายน้ำพิกัด GPS และหลักฐาน
        cv2.rectangle(evidence_frame, (0, h - 48), (w, h), (15, 15, 15), -1)
        cv2.rectangle(evidence_frame, (0, h - 48), (w, h - 46), banner_color, -1)

        cv2.putText(evidence_frame, watermark_text, (16, h - 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 1)

        # 1. บันทึกลงโฟลเดอร์ตามหมวดหมู่ (เช่น safe_start, mid_ride_violations)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        cv2.imwrite(filename, evidence_frame)

        # 2. บันทึกลงโฟลเดอร์รวม 'captures/all_captures/' (โฟลเดอร์รวมทุกภาพ ไม่ต้องแยกอะไร ดูได้ครบในที่เดียว)
        all_folder_path = os.path.join(self.captures_dir, 'all_captures', os.path.basename(filename))
        os.makedirs(os.path.dirname(all_folder_path), exist_ok=True)
        cv2.imwrite(all_folder_path, evidence_frame)

        # 3. บันทึกลงโฟลเดอร์หลัก 'captures/' โดยตรง (เปิดโฟลเดอร์มาเห็นภาพทั้งหมดทันที)
        root_path = os.path.join(self.captures_dir, os.path.basename(filename))
        if os.path.abspath(filename) != os.path.abspath(root_path):
            cv2.imwrite(root_path, evidence_frame)

    def handle_capture_events(self, frame, detections, is_violation):
        """บันทึกภาพตามเหตุการณ์จริง: ทั้งตอนสวมหมวกออกรถ และตอนถอดหมวกกลางคัน"""
        now = time.time()
        timestamp = datetime.now()

        # คำนวณเวลาจับเวลาระบบ (System Uptime Stopwatch)
        sys_uptime_sec = int(now - self.start_time)
        u_mins, u_secs = divmod(sys_uptime_sec, 60)
        sys_stopwatch_str = f"{u_mins:02d}m {u_secs:02d}s"

        # 🟢 EVENT 1: สวมหมวกปลดล็อคสตาร์ทรถสำเร็จ (Start Verified)
        if not is_violation and self.engine_started:
            if not self.has_captured_start:
                self.has_captured_start = True
                self.trip_start_time = now
                filename = os.path.join(self.captures_dir, 'safe_start', f"start_verified_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg")
                watermark = (
                    f"[PASS] SAFE START | HELMET VERIFIED | STOPWATCH: 00m 00s | "
                    f"SPEED: {self.current_speed:.1f} KM/H | GPS: {self.gps_lat:.6f} N, {self.gps_lon:.6f} E | "
                    f"TIME: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                self._save_evidence_image(frame, detections, filename, watermark, banner_color=(0, 200, 0))
                print(f"[SAFE START] 🟢 บันทึกภาพยืนยันการสวมหมวกออกรถ: {filename}")

        # 🔴 EVENT 2: ถอดหมวกกลางคันขณะขับขี่ (Mid-Ride Helmet Removal Violation)
        if is_violation and self.engine_started:
            just_removed = (self.last_known_helmet_state == True)
            driving_without_helmet = (self.current_speed > 3.0)

            if (just_removed or driving_without_helmet) and (now - self.last_violation_time > self.violation_cooldown):
                self.last_violation_time = now

                # คำนวณระยะเวลาตั้งแต่เริ่มสตาร์ทขับขี่ (Trip Stopwatch)
                duration_sec = int(now - self.trip_start_time) if self.trip_start_time else 0
                mins, secs = divmod(duration_sec, 60)
                trip_str = f"{mins:02d}m {secs:02d}s"

                filename = os.path.join(self.captures_dir, 'mid_ride_violations', f"mid_ride_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg")
                watermark = (
                    f"[ALERT] MID-RIDE HELMET REMOVAL | STOPWATCH: {trip_str} | "
                    f"SPEED: {self.current_speed:.1f} KM/H | GPS: {self.gps_lat:.6f} N, {self.gps_lon:.6f} E | "
                    f"TIME: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                self._save_evidence_image(frame, detections, filename, watermark, banner_color=(0, 0, 255))
                self._play_buzzer_sound()
                print(f"[MID-RIDE VIOLATION] 🚨 ตรวจพบถอดหมวกกลางคัน! ความเร็ว {self.current_speed:.1f} km/h, ขับขี่มาแล้ว {trip_str}, บันทึกภาพ: {filename}")

                # บันทึก JSON log
                violation_data = {
                    'type': 'MID_RIDE_HELMET_REMOVAL',
                    'timestamp': timestamp.isoformat(),
                    'speed_kmh': round(self.current_speed, 1),
                    'trip_duration': trip_str,
                    'gps': {
                        'latitude': round(self.gps_lat, 6),
                        'longitude': round(self.gps_lon, 6),
                        'satellites': self.gps_satellites
                    },
                    'image_file': filename
                }
                self.violations_log.append(violation_data)
                log_file = os.path.join(self.logs_dir, f"violations_{timestamp.strftime('%Y%m%d')}.json")
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump(self.violations_log, f, indent=2, ensure_ascii=False)

        # ⚠️ EVENT 3: ตรวจพบไม่สวมหมวก (ไม่ใช่ตอนถอดหมวกกลางคัน เช่น ขณะจอด / ก่อนออกรถ / พยายามสตาร์ท)
        if is_violation and not self.engine_started:
            if (now - self.last_no_helmet_time > self.no_helmet_cooldown):
                self.last_no_helmet_time = now
                filename = os.path.join(self.captures_dir, 'no_helmet', f"no_helmet_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg")
                watermark = (
                    f"[ALERT] NO HELMET DETECTED | STOPWATCH: {sys_stopwatch_str} | ENGINE LOCKED | "
                    f"SPEED: {self.current_speed:.1f} KM/H | GPS: {self.gps_lat:.6f} N, {self.gps_lon:.6f} E | "
                    f"TIME: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                self._save_evidence_image(frame, detections, filename, watermark, banner_color=(0, 0, 255))
                self._play_buzzer_sound()
                print(f"[NO HELMET] ⚠️ ตรวจพบไม่สวมหมวก (ก่อนออกรถ/ขณะจอด)! จับเวลา: {sys_stopwatch_str}, บันทึกภาพ: {filename}")

                # บันทึก JSON log
                violation_data = {
                    'type': 'INITIAL_NO_HELMET',
                    'timestamp': timestamp.isoformat(),
                    'speed_kmh': round(self.current_speed, 1),
                    'stopwatch_duration': sys_stopwatch_str,
                    'gps': {
                        'latitude': round(self.gps_lat, 6),
                        'longitude': round(self.gps_lon, 6),
                        'satellites': self.gps_satellites
                    },
                    'image_file': filename
                }
                self.violations_log.append(violation_data)
                log_file = os.path.join(self.logs_dir, f"violations_{timestamp.strftime('%Y%m%d')}.json")
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump(self.violations_log, f, indent=2, ensure_ascii=False)

        # อัปเดตสถานะหมวกเฟรมล่าสุด
        self.last_known_helmet_state = not is_violation

    def manual_capture(self, frame, detections, is_violation):
        """กดปุ่ม S เพื่อบันทึกภาพด้วยตนเอง (Manual Snapshot)"""
        now = time.time()
        timestamp = datetime.now()
        prefix = "manual_no_helmet" if is_violation else "manual_helmet"
        filename = os.path.join(self.captures_dir, 'manual_snapshots', f"{prefix}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg")

        status_text = "NO HELMET" if is_violation else "HELMET OK"
        banner_col = (0, 0, 255) if is_violation else (0, 200, 0)
        # คำนวณเวลาจับเวลา (Stopwatch)
        dur_sec = int(now - self.trip_start_time) if (self.engine_started and self.trip_start_time) else int(now - self.start_time)
        m_mins, m_secs = divmod(dur_sec, 60)
        dur_str = f"{m_mins:02d}m {m_secs:02d}s"

        watermark = (
            f"MANUAL SNAPSHOT | {status_text} | SPEED: {self.current_speed:.1f} KM/H | "
            f"STOPWATCH: {dur_str} | "
            f"GPS: {self.gps_lat:.6f} N, {self.gps_lon:.6f} E | "
            f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self._save_evidence_image(frame, detections, filename, watermark, banner_color=banner_col)
        print(f"[MANUAL SAVE] 📸 บันทึกภาพสถานะ ({status_text}): {filename}")

    def draw_hud(self, frame, detections, violation):
        """วาดหน้าปัดและแดชบอร์ดรถมอเตอร์ไซค์ไฟฟ้าเสมือนจริง (EV Motorcycle HUD)"""
        h, w = frame.shape[:2]

        # 1. วาดกรอบตรวจจับ (Bounding Boxes: Person, Helmet, Motorcycle)
        for det in detections:
            cls = det['class']
            conf = float(det['confidence'])
            bx, by, bw, bh = [int(v) for v in det['box']]

            if cls == 'helmet':
                color = (0, 230, 0)      # สีเขียวสด
                label = f"HELMET OK ({int(conf*100)}%)"
                text_color = (255, 255, 255)
                box_thickness = 3
            elif cls == 'no_helmet':
                color = (0, 0, 255)      # สีแดงสด
                label = f"NO HELMET ({int(conf*100)}%)"
                text_color = (255, 255, 255)
                box_thickness = 3
            elif cls == 'person':
                color = (255, 215, 0)    # สีเหลืองทอง
                label = f"PERSON ({int(conf*100)}%)"
                text_color = (20, 20, 20)
                box_thickness = 2
            elif cls == 'motorcycle':
                color = (255, 140, 0)    # สีส้ม
                label = f"MOTORCYCLE ({int(conf*100)}%)"
                text_color = (255, 255, 255)
                box_thickness = 2
            else:
                color = (200, 200, 200)
                label = f"{cls.upper()} ({int(conf*100)}%)"
                text_color = (0, 0, 0)
                box_thickness = 2

            cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), color, box_thickness)

            # ป้ายชื่อหัวมุม
            tw = len(label) * 9 + 10
            lbl_y1 = max(0, by - 26)
            lbl_y2 = max(26, by)
            cv2.rectangle(frame, (bx, lbl_y1), (bx + tw, lbl_y2), color, -1)
            cv2.putText(frame, label, (bx + 5, max(18, by - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, text_color, 2)

        # 2. แถบสถานะด้านบน (Top Status Bar)
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 55), (15, 15, 20), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        now_dt = datetime.now()
        current_time_str = now_dt.strftime('%H:%M:%S')
        current_date_str = now_dt.strftime('%Y-%m-%d')

        # คำนวณระบบจับเวลาการขับขี่ (Live Trip Stopwatch Timer)
        curr_now = time.time()
        if self.engine_started and self.trip_start_time is not None:
            elapsed_sec = int(curr_now - self.trip_start_time)
            hrs, rem = divmod(elapsed_sec, 3600)
            mins, secs = divmod(rem, 60)
            if hrs > 0:
                trip_timer_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
            else:
                trip_timer_str = f"{mins:02d}:{secs:02d}"
            timer_color = (0, 255, 200) # เขียวอมฟ้านีออน กำลังจับเวลาการขับขี่
        else:
            # ขณะจอดหรือเปิดเครื่องใหม่ ให้จับเวลา Uptime ของระบบ
            elapsed_sec = int(curr_now - self.start_time)
            mins, secs = divmod(elapsed_sec, 60)
            trip_timer_str = f"{mins:02d}:{secs:02d}"
            timer_color = (180, 220, 255) # ฟ้าอ่อน กำลังจับเวลาระบบ

        # หัวข้อระบบ (ด้านซ้าย)
        cv2.putText(frame, "E-MOTORCYCLE SMART HELMET SYSTEM", (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 2)

        # นาฬิกาบอกเวลาปัจจุบัน (Live Clock)
        cv2.putText(frame, f"TIME: {current_time_str}", (470, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 2)

        # ระบบจับเวลา (Live Stopwatch Timer)
        cv2.putText(frame, f"STOPWATCH: {trip_timer_str}", (670, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, timer_color, 2)

        # สถานะแบตเตอรี่รถไฟฟ้า
        bat_color = (0, 255, 0) if self.battery_percent > 30 else (0, 0, 255)
        cv2.putText(frame, f"BAT: {self.battery_voltage:.1f}V", (930, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, bat_color, 2)

        # สถานะ GPS
        cv2.putText(frame, f"GPS FIX ({self.gps_satellites} Sats)", (1090, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (100, 240, 255), 2)

        # 3. กล่องควบคุมฮาร์ดแวร์เสมือนจริง (Virtual Hardware Panel - ด้านขวา)
        rh_x = w - 340
        overlay2 = frame.copy()
        cv2.rectangle(overlay2, (rh_x, 70), (w - 15, 365), (10, 12, 18), -1)
        cv2.addWeighted(overlay2, 0.82, frame, 0.18, 0, frame)
        cv2.rectangle(frame, (rh_x, 70), (w - 15, 365), (70, 80, 95), 1)

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
        if not self.manual_override:
            mode_text = "AUTO (AI Tracking)"
            mode_col = (0, 255, 180)
        elif self.forced_helmet_state:
            mode_text = "MANUAL (HELMET ON)"
            mode_col = (0, 255, 0)
        else:
            mode_text = "MANUAL (NO HELMET)"
            mode_col = (0, 100, 255)
        cv2.putText(frame, f"Demo Mode: {mode_text}", (rh_x + 18, 312),
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

        # เวลาจับเวลาบนหน้าปัดเรือนไมล์ (Speedometer Stopwatch Display)
        cv2.putText(frame, f"STOPWATCH: {trip_timer_str}", (40, h - 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, timer_color, 2)

        # ข้อความสถานะคันเร่ง / สตาร์ท
        if self.engine_locked:
            throttle_status = "ENGINE: LOCKED (NO HELMET)"
            t_col = (0, 0, 255)
        else:
            throttle_status = "THROTTLE: APPLIED" if self.is_throttling else "THROTTLE: RELEASED"
            t_col = (0, 255, 0) if self.is_throttling else (180, 200, 220)
        cv2.putText(frame, throttle_status, (40, h - 72),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, t_col, 1)

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

        gps_info = (
            f"GPS: {self.gps_lat:.6f} N, {self.gps_lon:.6f} E | "
            f"SPEED: {self.current_speed:.1f} KM/H | "
            f"TIME: {current_time_str} | "
            f"TRIP DURATION: {trip_timer_str}"
        )
        cv2.putText(frame, gps_info, (20, h - 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 1)

        shortcuts = "[H] Toggle Helmet | [A] Auto AI | [T/Up] Throttle | [B/Down] Brake | [S] Capture | [R] Reset | [Q] Quit"
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
                
                # 4. ระบบบันทึกภาพอัจฉริยะตามเหตุการณ์จริง (Smart Event-Driven Capture)
                self.handle_capture_events(frame, detections, violation)
                
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
                    # สลับสถานะ: Auto -> Manual สวมหมวก -> Manual ไม่สวมหมวก -> กลับมา Auto
                    if not self.manual_override:
                        self.manual_override = True
                        self.forced_helmet_state = True
                        print("[DEMO CONTROL] บังคับสถานะ: สวมหมวกนิรภัย (HELMET ON)")
                    elif self.forced_helmet_state:
                        self.forced_helmet_state = False
                        print("[DEMO CONTROL] บังคับสถานะ: ไม่สวมหมวกนิรภัย (NO HELMET)")
                    else:
                        self.manual_override = False
                        print("[DEMO CONTROL] กลับสู่โหมด: ตรวจจับอัตโนมัติ (AUTO AI)")
                elif key == ord('a') or key == ord('A'):
                    self.manual_override = False
                    print("[DEMO CONTROL] กลับสู่โหมด: ตรวจจับอัตโนมัติ (AUTO AI)")
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
                    self.manual_capture(frame, detections, violation)
                elif key == ord('r') or key == ord('R'):
                    self.violations_log.clear()
                    self.current_speed = 0.0
                    self.target_speed = 45.0
                    self.manual_override = False
                    self.has_captured_start = False
                    self.trip_start_time = None
                    self.last_known_helmet_state = False
                    print("[RESET] รีเซ็ตสถิติและการเดินทางเรียบร้อย")
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
