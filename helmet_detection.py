import cv2
import numpy as np
from collections import deque
import time
import json
from datetime import datetime
import os

# =====================================================
# ระบบตรวจจับหมวกกันน็อคสำหรับรถมอเตอร์ไซค์ไฟฟ้า
# Helmet Detection System for Electric Motorcycles
# =====================================================
# ใช้ OpenCV + YOLO สำหรับการตรวจจับวัตถุ
# =====================================================


class HelmetDetectionSystem:
    """ระบบตรวจจับหมวกกันน็อคหลัก"""
    
    def __init__(self, config=None):
        """เริ่มต้นระบบ"""
        self.config = config or self._default_config()
        self.detection_history = deque(maxlen=100)
        self.alert_log = []
        self.frame_count = 0
        self.start_time = time.time()
        
        # สถานะ GPS (ATGM336H / NEO-M8N)
        self.current_gps = {
            'lat': 13.7563,
            'lon': 100.5018,
            'speed': 0.0,
            'satellites': 8,
            'fix': True
        }
        
        # สถานะหมวกนิรภัยล่าสุด
        self.last_helmet_status = True
        self.engine_started = False
        self.trip_start_time = None
        self.has_captured_start = False
        self.last_known_helmet_state = False

        # โหลด YOLO model
        self._load_model()
        
        # สร้างโฟลเดอร์สำหรับบันทึก
        os.makedirs('logs', exist_ok=True)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.captures_dir = os.path.join(self.base_dir, 'captures')
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        os.makedirs(self.captures_dir, exist_ok=True)
        os.makedirs(os.path.join(self.captures_dir, 'all_captures'), exist_ok=True) # โฟลเดอร์รวมทุกภาพ ไม่แยกหมวดหมู่
        os.makedirs(os.path.join(self.captures_dir, 'safe_start'), exist_ok=True)
        os.makedirs(os.path.join(self.captures_dir, 'mid_ride_violations'), exist_ok=True)
        os.makedirs(os.path.join(self.captures_dir, 'no_helmet'), exist_ok=True)  # โฟลเดอร์ตรวจพบไม่ใส่หมวก (ไม่ใช่ถอดกลางคัน)
        os.makedirs(os.path.join(self.captures_dir, 'manual_snapshots'), exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

        # เริ่มต้นส่ง Telemetry ไปยัง WebApp Server (localhost:5000)
        self._init_telemetry()

    def _init_telemetry(self):
        """เริ่มเธรดส่งข้อมูลพิกัด GPS จริงและความเร็วไปยัง WebApp Server แบบ Real-time"""
        import threading
        import urllib.request
        def telemetry_worker():
            while True:
                time.sleep(0.4)
                try:
                    payload = json.dumps({
                        'lat': self.current_gps['lat'],
                        'lon': self.current_gps['lon'],
                        'speed': self.current_gps['speed'],
                        'helmet': getattr(self, 'last_helmet_status', True),
                        'engine_locked': not getattr(self, 'last_helmet_status', True),
                        'satellites': self.current_gps['satellites'],
                        'source': 'Hardware System (Real)'
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
        
    def _default_config(self):
        """ค่าตั้งต้นของระบบ"""
        return {
            'model': {
                'weights': 'yolov4-helmet.weights',
                'config': 'yolov4-helmet.cfg',
                'names': 'helmet.names',
                'confidence_threshold': 0.5,
                'nms_threshold': 0.4,
                'input_size': (416, 416)
            },
            'camera': {
                'source': 0,  # 0 = webcam, หรือ URL/path
                'width': 1280,
                'height': 720,
                'fps': 30
            },
            'detection': {
                'classes': ['helmet', 'no_helmet', 'person', 'motorcycle'],
                'colors': {
                    'helmet': (0, 255, 0),      # เขียว - สวมหมวก
                    'no_helmet': (0, 0, 255),    # แดง - ไม่สวมหมวก
                    'person': (255, 255, 0),     # เหลือง - คน
                    'motorcycle': (255, 165, 0)  # ส้ม - มอเตอร์ไซค์
                }
            },
            'alert': {
                'enabled': True,
                'cooldown': 5,  # วินาที
                'capture_violation': True,
                'sound_alert': True
            },
            'gps': {
                'enabled': True,
                'module': 'ATGM336H / NEO-M8N',
                'default_lat': 13.75633,
                'default_lon': 100.50177
            },
            'electric_motorcycle': {
                'speed_limit_no_helmet': 25,  # km/h
                'auto_limit_speed': True,
                'serial_port': '/dev/ttyAMA0' if RPI_AVAILABLE else '/dev/ttyUSB0',
                'baud_rate': 9600,
                'gpio_pins': {
                    'relay': 17,     # คุม Relay จำกัดความเร็ว / ตัดคันเร่ง
                    'buzzer': 27,    # ขับสัญญาณเสียงเตือน Buzzer
                    'led_green': 22, # ไฟเขียว (สวมหมวก/ปลอดภัย)
                    'led_red': 23    # ไฟแดง (ไม่สวมหมวก/อันตราย)
                }
            }
        }
    
    def _load_model(self):
        """โหลด YOLO model สำหรับตรวจจับ"""
        try:
            model_cfg = self.config['model']
            
            # ลองโหลด YOLO model
            if os.path.exists(model_cfg['weights']) and os.path.exists(model_cfg['config']):
                self.net = cv2.dnn.readNetFromDarknet(
                    model_cfg['config'], 
                    model_cfg['weights']
                )
                
                # ใช้ GPU ถ้ามี
                if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                    self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                    self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
                    print("[INFO] ใช้ GPU สำหรับการประมวลผล")
                else:
                    self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                    self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                    print("[INFO] ใช้ CPU สำหรับการประมวลผล")
                
                # โหลดชื่อ classes
                if os.path.exists(model_cfg['names']):
                    with open(model_cfg['names'], 'r') as f:
                        self.classes = [line.strip() for line in f.readlines()]
                else:
                    self.classes = self.config['detection']['classes']
                
                self.output_layers = self.net.getUnconnectedOutLayersNames()
                self.model_loaded = True
                print("[INFO] โหลด YOLO model สำเร็จ")
            else:
                print("[WARNING] ไม่พบไฟล์ model - ใช้โหมดจำลอง")
                self.model_loaded = False
                self._setup_demo_mode()
                
        except Exception as e:
            print(f"[ERROR] ไม่สามารถโหลด model: {e}")
            self.model_loaded = False
            self._setup_demo_mode()
    
    def _setup_demo_mode(self):
        """ตั้งค่าโหมดจำลองสำหรับทดสอบ"""
        self.net = None
        self.classes = self.config['detection']['classes']
        self.output_layers = []
        
        # ใช้ Haar Cascade สำหรับตรวจจับใบหน้า (โหมดจำลอง)
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # ใช้ Background Subtractor สำหรับตรวจจับการเคลื่อนไหว
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=True
        )
        print("[INFO] ใช้โหมดจำลอง (Demo Mode)")
    
    def detect_objects(self, frame):
        """ตรวจจับวัตถุในเฟรม"""
        if self.model_loaded:
            return self._detect_with_yolo(frame)
        else:
            return self._detect_demo_mode(frame)
    
    def _detect_with_yolo(self, frame):
        """ตรวจจับด้วย YOLO"""
        height, width = frame.shape[:2]
        input_size = self.config['model']['input_size']
        conf_threshold = self.config['model']['confidence_threshold']
        nms_threshold = self.config['model']['nms_threshold']
        
        # สร้าง blob จากรูปภาพ
        blob = cv2.dnn.blobFromImage(
            frame, 1/255.0, input_size, 
            swapRB=True, crop=False
        )
        self.net.setInput(blob)
        outputs = self.net.forward(self.output_layers)
        
        boxes = []
        confidences = []
        class_ids = []
        
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if confidence > conf_threshold:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        # Non-Maximum Suppression
        indices = cv2.dnn.NMSBoxes(
            boxes, confidences, conf_threshold, nms_threshold
        )
        
        detections = []
        if len(indices) > 0:
            for i in indices.flatten():
                detections.append({
                    'class': self.classes[class_ids[i]],
                    'confidence': confidences[i],
                    'box': boxes[i],
                    'class_id': class_ids[i]
                })
        
        return detections
    
    def _detect_demo_mode(self, frame):
        """ตรวจจับในโหมดจำลอง"""
        detections = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # ตรวจจับใบหน้า
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
        )
        
        for (x, y, w, h) in faces:
            # ตรวจสอบพื้นที่เหนือศีรษะ
            helmet_region_y = max(0, y - int(h * 0.8))
            helmet_region = gray[helmet_region_y:y, x:x+w]
            
            if helmet_region.size > 0:
                # วิเคราะห์พื้นที่เหนือศีรษะ
                mean_val = np.mean(helmet_region)
                std_val = np.std(helmet_region)
                edges = cv2.Canny(helmet_region, 50, 150)
                edge_density = np.sum(edges > 0) / edges.size if edges.size > 0 else 0
                
                # ตัดสินใจ (simplified)
                has_helmet = edge_density > 0.15 and std_val > 30
                
                if has_helmet:
                    detections.append({
                        'class': 'helmet',
                        'confidence': min(0.7 + edge_density, 0.95),
                        'box': [x, helmet_region_y, w, y - helmet_region_y + h],
                        'class_id': 0
                    })
                else:
                    detections.append({
                        'class': 'no_helmet',
                        'confidence': 0.6,
                        'box': [x, y, w, h],
                        'class_id': 1
                    })
            
            # เพิ่ม person detection
            detections.append({
                'class': 'person',
                'confidence': 0.8,
                'box': [x - 20, y - 10, w + 40, h + 100],
                'class_id': 2
            })
        
        # ตรวจจับการเคลื่อนไหว (จำลองมอเตอร์ไซค์)
        fg_mask = self.bg_subtractor.apply(frame)
        contours, _ = cv2.findContours(
            fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 5000:  # พื้นที่ขั้นต่ำ
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                if 0.5 < aspect_ratio < 3.0:  # สัดส่วนคล้ายมอเตอร์ไซค์
                    detections.append({
                        'class': 'motorcycle',
                        'confidence': 0.5,
                        'box': [x, y, w, h],
                        'class_id': 3
                    })
        
        return detections
    
    def draw_detections(self, frame, detections):
        """วาดผลการตรวจจับลงบนเฟรม"""
        colors = self.config['detection']['colors']
        violation_detected = False
        
        for det in detections:
            cls = det['class']
            conf = det['confidence']
            x, y, w, h = det['box']
            
            color = colors.get(cls, (128, 128, 128))
            
            # วาดกรอบ
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # ป้ายชื่อ
            label = f"{cls}: {conf:.2f}"
            label_size, baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            
            # พื้นหลังป้ายชื่อ
            cv2.rectangle(
                frame, 
                (x, y - label_size[1] - 10), 
                (x + label_size[0], y),
                color, -1
            )
            cv2.putText(
                frame, label, (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
            )
            
            # ตรวจสอบการละเมิด
            if cls == 'no_helmet':
                violation_detected = True
                self._draw_warning(frame, x, y, w, h)
        
        return frame, violation_detected
    
    def _draw_warning(self, frame, x, y, w, h):
        """วาดคำเตือนสำหรับการไม่สวมหมวก"""
        # กรอบเตือนกระพริบ
        if int(time.time() * 2) % 2 == 0:
            cv2.rectangle(
                frame, (x - 5, y - 5), 
                (x + w + 5, y + h + 5), 
                (0, 0, 255), 3
            )
        
        # ข้อความเตือน
        warning_text = "WARNING: NO HELMET!"
        text_size = cv2.getTextSize(
            warning_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2
        )[0]
        
        text_x = x + (w - text_size[0]) // 2
        text_y = y + h + 30
        
        cv2.rectangle(
            frame,
            (text_x - 5, text_y - text_size[1] - 5),
            (text_x + text_size[0] + 5, text_y + 5),
            (0, 0, 255), -1
        )
        cv2.putText(
            frame, warning_text, (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2
        )
    
    def draw_dashboard(self, frame):
        """วาด Dashboard แสดงสถานะ และแถบระบบจับเวลาสด (Live Stopwatch / Time Display)"""
        height, width = frame.shape[:2]
        now = time.time()
        now_time_str = datetime.now().strftime('%H:%M:%S')

        # 1. คำนวณระบบจับเวลา (Live Stopwatch Calculation)
        if self.engine_started and self.trip_start_time is not None:
            trip_sec = int(now - self.trip_start_time)
            hrs, rem = divmod(trip_sec, 3600)
            mins, secs = divmod(rem, 60)
            if hrs > 0:
                stopwatch_display = f"{hrs:02d}:{mins:02d}:{secs:02d}"
            else:
                stopwatch_display = f"{mins:02d}:{secs:02d}"
            timer_label = "RIDING"
            timer_color = (0, 255, 200) # เขียวอมฟ้านีออน กำลังจับเวลาการขับขี่
        else:
            uptime_sec = int(now - self.start_time)
            mins, secs = divmod(uptime_sec, 60)
            stopwatch_display = f"{mins:02d}:{secs:02d}"
            timer_label = "UPTIME"
            timer_color = (180, 220, 255) # ฟ้าอ่อน กำลังจับเวลาระบบ

        # 2. แถบสถานะด้านบน (Top Bar) แสดงเวลาและนาฬิกาจับเวลาชัดเจน
        overlay_top = frame.copy()
        cv2.rectangle(overlay_top, (0, 0), (width, 42), (12, 14, 20), -1)
        cv2.addWeighted(overlay_top, 0.85, frame, 0.15, 0, frame)

        # หัวข้อระบบ
        cv2.putText(frame, "HELMET SAFETY SYSTEM", (15, 27),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 2)

        # นาฬิกาบอกเวลาปัจจุบัน (Live Clock)
        time_x = max(240, width // 2 - 120)
        cv2.putText(frame, f"TIME: {now_time_str}", (time_x, 27),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 2)

        # ระบบจับเวลาสด (Live Stopwatch) เด่นชัดด้วยสีนีออน
        sw_x = max(420, width - 270)
        cv2.putText(frame, f"STOPWATCH: {stopwatch_display}", (sw_x, 27),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.54, timer_color, 2)

        # 3. กล่อง Dashboard แสดงสถิติและข้อมูลระบบ (ด้านซ้าย)
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 52), (380, 280), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)

        cv2.putText(
            frame, "System Telemetry / Status", (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 255, 255), 2
        )
        cv2.line(frame, (20, 84), (370, 84), (0, 255, 255), 1)

        elapsed = now - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0

        engine_status = "STARTED (READY)" if self.engine_started else "LOCKED (OFF)"
        mode_name = "YOLO" if self.model_loaded else "Demo"
        info_lines = [
            (f"FPS: {fps:.1f} | Frame: {self.frame_count}", (200, 200, 200)),
            (f"Clock Time: {now_time_str}", (255, 255, 255)),
            (f"Stopwatch ({timer_label}): {stopwatch_display}", timer_color),
            (f"Engine: {engine_status}", (0, 255, 0) if self.engine_started else (0, 0, 255)),
            (f"Speed: {self.current_gps['speed']:.1f} km/h (Sats: {self.current_gps['satellites']})", (100, 240, 255)),
            (f"GPS: {self.current_gps['lat']:.5f}, {self.current_gps['lon']:.5f}", (200, 200, 200)),
            (f"Violations: {len(self.alert_log)} | Mode: {mode_name}", (255, 180, 0))
        ]

        for i, (line, col) in enumerate(info_lines):
            cv2.putText(
                frame, line, (20, 108 + i * 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.46, col, 1
            )

        return frame
    
    def process_violation(self, frame, detections):
        """บันทึกข้อมูลและภาพถ่ายหลักฐานการละเมิด (รองรับการตรวจจับถอดหมวกกลางคัน)"""
        timestamp = datetime.now()
        speed = self.current_gps['speed']
        now = time.time()

        is_mid_ride = self.engine_started or (speed > 3.0)
        duration_sec = int(now - self.trip_start_time) if self.trip_start_time else 0
        mins, secs = divmod(duration_sec, 60)
        trip_str = f"{mins:02d}m {secs:02d}s"

        violation_type = "MID_RIDE_HELMET_REMOVAL" if is_mid_ride else "NO_HELMET_VIOLATION"
        file_prefix = "mid_ride_violation" if is_mid_ride else "violation"

        violation = {
            'type': violation_type,
            'timestamp': timestamp.isoformat(),
            'frame_number': self.frame_count,
            'trip_duration': trip_str if is_mid_ride else "00m 00s",
            'gps': {
                'latitude': self.current_gps['lat'],
                'longitude': self.current_gps['lon'],
                'speed_kmh': speed,
                'satellites': self.current_gps['satellites'],
                'module': self.config.get('gps', {}).get('module', 'ATGM336H / NEO-M8N')
            },
            'detections': [{
                'class': d['class'],
                'confidence': d['confidence'],
                'box': d['box']
            } for d in detections if d['class'] == 'no_helmet']
        }

        self.alert_log.append(violation)

        # บันทึกภาพพร้อมประทับลายน้ำพิกัด GPS และวาดกรอบตรวจจับ
        if self.config['alert']['capture_violation']:
            # แยกโฟลเดอร์ระหว่างถอดหมวกกลางคัน (mid_ride_violations) กับตรวจพบไม่ใส่หมวกตั้งแต่แรก/ขณะจอด (no_helmet)
            target_sub = 'mid_ride_violations' if is_mid_ride else 'no_helmet'
            prefix = 'mid_ride_violation' if is_mid_ride else 'no_helmet'
            folder = os.path.join(self.captures_dir, target_sub)
            os.makedirs(folder, exist_ok=True)
            filename = os.path.join(folder, f"{prefix}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg")
            annotated_frame, _ = self.draw_detections(frame.copy(), detections)
            h, w = annotated_frame.shape[:2]

            # แถบดำด้านล่างภาพสำหรับลายน้ำพิกัดและเวลาจับเวลา
            cv2.rectangle(annotated_frame, (0, h - 45), (w, h), (15, 15, 15), -1)
            cv2.rectangle(annotated_frame, (0, h - 45), (w, h - 43), (0, 0, 255), -1)

            if is_mid_ride:
                watermark_text = f"[ALERT] MID-RIDE HELMET REMOVAL | STOPWATCH: {trip_str} | SPEED: {speed:.1f} km/h | GPS: {self.current_gps['lat']:.5f}, {self.current_gps['lon']:.5f} | TIME: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                uptime_sec = int(now - self.start_time)
                u_m, u_s = divmod(uptime_sec, 60)
                up_str = f"{u_m:02d}m {u_s:02d}s"
                watermark_text = f"[ALERT] NO HELMET DETECTED | STOPWATCH: {up_str} | SPEED: {speed:.1f} km/h | GPS: {self.current_gps['lat']:.5f}, {self.current_gps['lon']:.5f} | TIME: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

            cv2.putText(annotated_frame, watermark_text, (12, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 255), 1)

            cv2.imwrite(filename, annotated_frame)
            all_path = os.path.join(self.captures_dir, 'all_captures', os.path.basename(filename))
            cv2.imwrite(all_path, annotated_frame)
            root_path = os.path.join(self.captures_dir, os.path.basename(filename))
            if os.path.abspath(filename) != os.path.abspath(root_path):
                cv2.imwrite(root_path, annotated_frame)
            violation['image'] = filename
            print(f"[ALERT] 🚨 บันทึกภาพหลักฐาน ({violation_type}): {filename}")

        # ส่งสัญญาณจำกัดความเร็ว
        if self.config['electric_motorcycle']['auto_limit_speed']:
            self._send_speed_limit_command()

        # บันทึก log
        self._save_log(violation)

        return violation

    def capture_start_verified(self, frame, detections):
        """บันทึกภาพยืนยันการสวมหมวกและสตาร์ทรถสำเร็จ (Start Verified)"""
        timestamp = datetime.now()
        filename = os.path.join(self.captures_dir, 'safe_start', f"start_verified_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg")
        annotated_frame, _ = self.draw_detections(frame.copy(), detections)
        h, w = annotated_frame.shape[:2]

        cv2.rectangle(annotated_frame, (0, h - 45), (w, h), (15, 15, 15), -1)
        cv2.rectangle(annotated_frame, (0, h - 45), (w, h - 43), (0, 200, 0), -1)
        watermark_text = f"[PASS] SAFE START | HELMET VERIFIED | STOPWATCH: 00m 00s | SPEED: {self.current_gps['speed']:.1f} km/h | GPS: {self.current_gps['lat']:.5f}, {self.current_gps['lon']:.5f} | TIME: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        cv2.putText(annotated_frame, watermark_text, (12, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 255), 1)

        cv2.imwrite(filename, annotated_frame)
        all_path = os.path.join(self.captures_dir, 'all_captures', os.path.basename(filename))
        cv2.imwrite(all_path, annotated_frame)
        root_path = os.path.join(self.captures_dir, os.path.basename(filename))
        if os.path.abspath(filename) != os.path.abspath(root_path):
            cv2.imwrite(root_path, annotated_frame)
        print(f"[SAFE START] 🟢 บันทึกภาพยืนยันการสวมหมวกออกรถ: {filename}")

    def _send_speed_limit_command(self):
        """ส่งคำสั่งจำกัดความเร็วไปยังตัวควบคุมมอเตอร์"""
        speed_limit = self.config['electric_motorcycle']['speed_limit_no_helmet']
        if hasattr(self, 'controller') and self.controller and self.controller.is_connected:
            self.controller.set_speed_limit(speed_limit)
        else:
            print(f"[SIM] จำลองจำกัดความเร็ว: {speed_limit} km/h")
    
    def _save_log(self, violation):
        """บันทึก log การละเมิด"""
        log_file = f"logs/violations_{datetime.now().strftime('%Y%m%d')}.json"
        
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            logs.append(violation)
            
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"[ERROR] ไม่สามารถบันทึก log: {e}")
    
    def run(self, source=None):
        """เริ่มต้นระบบตรวจจับ"""
        source = source or self.config['camera']['source']
        
        print("=" * 60)
        print(" ระบบตรวจจับหมวกกันน็อค - Electric Motorcycle")
        print("=" * 60)
        print(f" แหล่งวิดีโอ: {source}")
        print(f" โหมด: {'YOLO' if self.model_loaded else 'Demo (Haar Cascade)'}")
        print(f" โมดูล GPS: {self.config.get('gps', {}).get('module', 'ATGM336H / NEO-M8N')}")
        print("=" * 60)
        print(" กด 'q' เพื่อออก | 's' เพื่อบันทึกภาพ | 'r' เพื่อรีเซ็ต")
        print("=" * 60)
        
        # เชื่อมต่อกับตัวควบคุมมอเตอร์และโมดูล GPS
        motor_cfg = self.config.get('electric_motorcycle', {})
        self.controller = ElectricMotorcycleController(
            port=motor_cfg.get('serial_port'),
            baud_rate=motor_cfg.get('baud_rate', 9600),
            gpio_config=motor_cfg.get('gpio_pins')
        )
        self.controller.connect()
        
        cap = cv2.VideoCapture(source)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config['camera']['width'])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config['camera']['height'])
        
        if not cap.isOpened():
            print("[ERROR] ไม่สามารถเปิดกล้องได้")
            return
        
        last_alert_time = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("[ERROR] ไม่สามารถอ่านเฟรมได้")
                    break
                
                self.frame_count += 1
                
                # อ่านอัปเดตข้อมูลพิกัดจาก GPS ATGM336H จริง (ถ้ามี)
                if self.controller and self.controller.is_connected:
                    gps_update = self.controller.read_gps_data()
                    if gps_update:
                        self.current_gps.update(gps_update)
                
                # ตรวจจับวัตถุ
                detections = self.detect_objects(frame)
                self.detection_history.extend(detections)
                
                # วาดผลการตรวจจับ
                frame, violation = self.draw_detections(frame, detections)
                self.last_helmet_status = not violation
                
                # วาด Dashboard
                frame = self.draw_dashboard(frame)
                
                # จัดการบันทึกภาพตามเหตุการณ์ (Start Verified vs Violation)
                if not violation:
                    if not self.has_captured_start:
                        self.has_captured_start = True
                        self.engine_started = True
                        self.trip_start_time = time.time()
                        self.capture_start_verified(frame, detections)
                else:
                    current_time = time.time()
                    cooldown = self.config['alert']['cooldown']
                    
                    if current_time - last_alert_time > cooldown:
                        self.process_violation(frame, detections)
                        last_alert_time = current_time
                        
                        # แสดงข้อความเตือนใหญ่
                        h, w = frame.shape[:2]
                        cv2.putText(
                            frame, "! HELMET REQUIRED !",
                            (w // 2 - 200, h - 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2,
                            (0, 0, 255), 3
                        )
                
                # แสดงผล
                cv2.imshow('Helmet Detection System', frame)

                # ตรวจจับการกดปุ่มกากบาท [X] ปิดหน้าต่าง (ป้องกันค้างบน Windows)
                try:
                    if cv2.getWindowProperty('Helmet Detection System', cv2.WND_PROP_VISIBLE) < 1:
                        break
                except Exception:
                    pass
                
                # จัดการ keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    timestamp = datetime.now()
                    now = time.time()
                    dur_sec = int(now - self.trip_start_time) if (self.engine_started and self.trip_start_time) else int(now - self.start_time)
                    m_mins, m_secs = divmod(dur_sec, 60)
                    dur_str = f"{m_mins:02d}m {m_secs:02d}s"
                    status_text = "HELMET OK" if self.last_helmet_status else "NO HELMET"
                    banner_col = (0, 200, 0) if self.last_helmet_status else (0, 0, 255)

                    filename = os.path.join(self.captures_dir, 'manual_snapshots', f"manual_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg")
                    annotated_frame, _ = self.draw_detections(frame.copy(), detections)
                    h, w = annotated_frame.shape[:2]
                    cv2.rectangle(annotated_frame, (0, h - 45), (w, h), (15, 15, 15), -1)
                    cv2.rectangle(annotated_frame, (0, h - 45), (w, h - 43), banner_col, -1)
                    watermark_text = f"MANUAL SNAPSHOT | {status_text} | STOPWATCH: {dur_str} | SPEED: {self.current_gps['speed']:.1f} km/h | GPS: {self.current_gps['lat']:.5f}, {self.current_gps['lon']:.5f} | TIME: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                    cv2.putText(annotated_frame, watermark_text, (12, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 255), 1)

                    cv2.imwrite(filename, annotated_frame)
                    all_path = os.path.join(self.captures_dir, 'all_captures', os.path.basename(filename))
                    cv2.imwrite(all_path, annotated_frame)
                    root_path = os.path.join(self.captures_dir, os.path.basename(filename))
                    if os.path.abspath(filename) != os.path.abspath(root_path):
                        cv2.imwrite(root_path, annotated_frame)
                    print(f"[SAVE] 📸 บันทึกภาพ Snapshot ({status_text}): {filename}")
                elif key == ord('r'):
                    self.detection_history.clear()
                    self.alert_log.clear()
                    self.frame_count = 0
                    self.start_time = time.time()
                    print("[RESET] รีเซ็ตระบบ")
                    
        except KeyboardInterrupt:
            print("\n[INFO] หยุดระบบ...")
        finally:
            if hasattr(self, 'controller') and self.controller:
                self.controller.disconnect()
            cap.release()
            cv2.destroyAllWindows()
            for _ in range(5):
                cv2.waitKey(1)
            self._generate_report()
    
    def _generate_report(self):
        """สร้างรายงานสรุป"""
        elapsed = time.time() - self.start_time
        
        report = {
            'summary': {
                'total_frames': self.frame_count,
                'runtime_seconds': round(elapsed, 2),
                'average_fps': round(self.frame_count / elapsed, 2) if elapsed > 0 else 0,
                'total_violations': len(self.alert_log),
                'mode': 'YOLO' if self.model_loaded else 'Demo',
                'gps_module': self.config.get('gps', {}).get('module', 'ATGM336H / NEO-M8N'),
                'last_known_gps': self.current_gps
            },
            'violations': self.alert_log
        }
        
        report_file = f"logs/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 60)
        print(" รายงานสรุป")
        print("=" * 60)
        print(f" จำนวนเฟรม: {report['summary']['total_frames']}")
        print(f" เวลาทำงาน: {report['summary']['runtime_seconds']} วินาที")
        print(f" FPS เฉลี่ย: {report['summary']['average_fps']}")
        print(f" การละเมิดทั้งหมด: {report['summary']['total_violations']}")
        print(f" พิกัด GPS ล่าสุด: Lat {self.current_gps['lat']:.5f}, Lon {self.current_gps['lon']:.5f}")
        print(f" รายงานบันทึกที่: {report_file}")
        print("=" * 60)


# ตรวจสอบการใช้งานบนบอร์ด Raspberry Pi 4
try:
    import RPi.GPIO as GPIO
    RPI_AVAILABLE = True
except (ImportError, RuntimeError):
    RPI_AVAILABLE = False


class ElectricMotorcycleController:
    """ตัวควบคุมรถมอเตอร์ไซค์ไฟฟ้าจริง (รองรับทั้ง Raspberry Pi 4 GPIO และ Serial เชื่อมต่อ Arduino)"""
    
    def __init__(self, port=None, baud_rate=9600, gpio_config=None):
        self.port = port or ('/dev/ttyAMA0' if RPI_AVAILABLE else '/dev/ttyUSB0')
        self.baud_rate = baud_rate
        self.current_speed_limit = None
        self.is_connected = False
        self.helmet_status = 'unknown'
        self.serial = None
        
        # กำหนดขา GPIO บน Raspberry Pi 4
        self.gpio_cfg = gpio_config or {
            'relay': 17,     # สั่ง Relay ดึงสาย Speed Limit / Throttle
            'buzzer': 27,    # สัญญาณเสียงเตือน Buzzer
            'led_green': 22, # ไฟเขียว: สวมหมวก (ปลอดภัย)
            'led_red': 23    # ไฟแดง: ไม่สวมหมวก (อันตราย)
        }
        
    def connect(self):
        """เริ่มต้นการเชื่อมต่อฮาร์ดแวร์บน Raspberry Pi 4 หรือ Serial"""
        # 1. ตั้งค่า GPIO บน Raspberry Pi 4
        if RPI_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                for pin in self.gpio_cfg.values():
                    GPIO.setup(pin, GPIO.OUT)
                
                # ค่าเริ่มต้น: สถานะปลอดภัย (Relay OFF, ไฟเขียว ON)
                GPIO.output(self.gpio_cfg['relay'], GPIO.LOW)
                GPIO.output(self.gpio_cfg['buzzer'], GPIO.LOW)
                GPIO.output(self.gpio_cfg['led_green'], GPIO.HIGH)
                GPIO.output(self.gpio_cfg['led_red'], GPIO.LOW)
                self.is_connected = True
                print(f"[RPI-4] เริ่มต้นระบบ GPIO ควบคุมรถมอเตอร์ไซค์ไฟฟ้าสำเร็จ (Relay PIN {self.gpio_cfg['relay']})")
            except Exception as e:
                print(f"[RPI-4] ตั้งค่า GPIO ไม่สำเร็จ: {e}")
        
        # 2. เชื่อมต่อ Serial สำหรับอ่านพิกัด GPS ATGM336H หรือสื่อสารกล่องคอนโทรลเลอร์
        try:
            import serial
            self.serial = serial.Serial(self.port, self.baud_rate, timeout=1)
            self.is_connected = True
            print(f"[HARDWARE] เชื่อมต่อพอร์ต {self.port} สำเร็จ")
        except Exception as e:
            if not RPI_AVAILABLE:
                print(f"[HARDWARE] จำลองการทำงาน (ไม่พบพอร์ต Serial: {e})")
            else:
                print(f"[HARDWARE] GPS Serial บน {self.port}: {e}")
    
    def set_speed_limit(self, max_speed):
        """ตั้งค่าจำกัดความเร็วบนรถมอเตอร์ไซค์ไฟฟ้าจริง"""
        self.current_speed_limit = max_speed
        
        # ควบคุมฮาร์ดแวร์จริงบน Raspberry Pi 4
        if RPI_AVAILABLE:
            try:
                # สั่ง Relay ทำงานเพื่อดึงสาย Speed Limit ลง GND หรือตัดแรงดันคันเร่ง
                GPIO.output(self.gpio_cfg['relay'], GPIO.HIGH)
                GPIO.output(self.gpio_cfg['led_green'], GPIO.LOW)
                GPIO.output(self.gpio_cfg['led_red'], GPIO.HIGH)
                GPIO.output(self.gpio_cfg['buzzer'], GPIO.HIGH)
                print(f"[RPI-4 HW] สั่ง Relay (PIN {self.gpio_cfg['relay']}) ดึงสาย Speed Limit: จำกัดความเร็ว {max_speed} km/h")
            except Exception as e:
                print(f"[RPI-4 HW Error]: {e}")
        
        # ส่งคำสั่งผ่าน Serial ไปยัง Arduino / กล่องคอนโทรลเลอร์ (ถ้ามี)
        if self.serial and self.serial.is_open:
            try:
                command = f"SPEED_LIMIT:{max_speed}\n"
                self.serial.write(command.encode())
                print(f"[MOTOR SERIAL] ส่งคำสั่งจำกัดความเร็ว: {max_speed} km/h")
            except Exception as e:
                print(f"[MOTOR SERIAL Error]: {e}")
        elif not RPI_AVAILABLE:
            print(f"[SIM] จำลองจำกัดความเร็วรถ: {max_speed} km/h")
    
    def remove_speed_limit(self):
        """ยกเลิกการจำกัดความเร็ว (อนุญาตให้ขับขี่ด้วยความเร็วปกติ)"""
        self.current_speed_limit = None
        
        # ปลด Relay บน Raspberry Pi 4
        if RPI_AVAILABLE:
            try:
                GPIO.output(self.gpio_cfg['relay'], GPIO.LOW)
                GPIO.output(self.gpio_cfg['led_green'], GPIO.HIGH)
                GPIO.output(self.gpio_cfg['led_red'], GPIO.LOW)
                GPIO.output(self.gpio_cfg['buzzer'], GPIO.LOW)
                print("[RPI-4 HW] ปลด Relay: สวมหมวกนิรภัยแล้ว ขับขี่ความเร็วปกติได้")
            except Exception as e:
                print(f"[RPI-4 HW Error]: {e}")
        
        if self.serial and self.serial.is_open:
            try:
                command = "SPEED_LIMIT:NONE\n"
                self.serial.write(command.encode())
                print("[MOTOR SERIAL] ยกเลิกจำกัดความเร็ว (Normal Speed)")
            except Exception as e:
                print(f"[MOTOR SERIAL Error]: {e}")
        elif not RPI_AVAILABLE:
            print("[SIM] ยกเลิกจำกัดความเร็ว (Normal Speed)")
    
    def update_helmet_status(self, status):
        """อัปเดตสถานะหมวกกันน็อค"""
        self.helmet_status = status
        if status == 'no_helmet':
            self.set_speed_limit(25)  # จำกัดความเร็ว 25 km/h
        elif status == 'helmet':
            self.remove_speed_limit()
    
    def read_gps_data(self):
        """อ่านและแปลงข้อมูลพิกัดจาก GPS ATGM336H / NEO-M8N"""
        if not self.serial or not self.serial.is_open:
            return None
        try:
            if self.serial.in_waiting > 0:
                line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                # 1. ตรวจสอบฟอร์แมตจาก Arduino
                if line.startswith("GPS:"):
                    parts = line[4:].split(',')
                    if len(parts) >= 5:
                        return {
                            'lat': float(parts[0]),
                            'lon': float(parts[1]),
                            'speed': float(parts[2]),
                            'satellites': int(parts[3]),
                            'fix': parts[4] == '1'
                        }
                # 2. ตรวจสอบประโยคดิบ NMEA $GNRMC / $GPRMC จากโมดูล GPS ต่อตรง Pi 4
                elif line.startswith("$GNRMC") or line.startswith("$GPRMC"):
                    parts = line.split(',')
                    if len(parts) >= 8 and parts[2] == 'A':
                        raw_lat = float(parts[3])
                        lat_deg = int(raw_lat / 100)
                        lat_min = raw_lat - (lat_deg * 100)
                        lat = lat_deg + (lat_min / 60.0)
                        if parts[4] == 'S': lat = -lat
                        
                        raw_lon = float(parts[5])
                        lon_deg = int(raw_lon / 100)
                        lon_min = raw_lon - (lon_deg * 100)
                        lon = lon_deg + (lon_min / 60.0)
                        if parts[6] == 'W': lon = -lon
                        
                        speed_knots = float(parts[7]) if parts[7] else 0.0
                        return {
                            'lat': lat,
                            'lon': lon,
                            'speed': speed_knots * 1.852,
                            'satellites': 8,
                            'fix': True
                        }
        except Exception:
            pass
        return None

    def disconnect(self):
        """ตัดการเชื่อมต่อและคืนค่าพิน GPIO ปลอดภัย"""
        if RPI_AVAILABLE:
            try:
                # ปิดรีเลย์ก่อนปิดโปรแกรมเพื่อความปลอดภัย
                GPIO.output(self.gpio_cfg['relay'], GPIO.LOW)
                GPIO.output(self.gpio_cfg['buzzer'], GPIO.LOW)
                GPIO.cleanup()
                print("[RPI-4] คืนค่าพิน GPIO สำเร็จ")
            except Exception:
                pass
        
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
                print("[HARDWARE] ปิดการเชื่อมต่อ Serial")
            except Exception:
                pass
        self.is_connected = False


# =====================================================
# ฟังก์ชันหลัก
# =====================================================
def main():
    """ฟังก์ชันหลักสำหรับเริ่มต้นระบบ"""
    
    # ตั้งค่าระบบ
    config = {
        'model': {
            'weights': 'yolov4-helmet.weights',
            'config': 'yolov4-helmet.cfg',
            'names': 'helmet.names',
            'confidence_threshold': 0.5,
            'nms_threshold': 0.4,
            'input_size': (416, 416)
        },
        'camera': {
            'source': 0,  # ใช้ webcam
            'width': 1280,
            'height': 720,
            'fps': 30
        },
        'detection': {
            'classes': ['helmet', 'no_helmet', 'person', 'motorcycle'],
            'colors': {
                'helmet': (0, 255, 0),
                'no_helmet': (0, 0, 255),
                'person': (255, 255, 0),
                'motorcycle': (255, 165, 0)
            }
        },
        'alert': {
            'enabled': True,
            'cooldown': 5,
            'capture_violation': True,
            'sound_alert': True
        },
        'gps': {
            'enabled': True,
            'module': 'ATGM336H / NEO-M8N',
            'default_lat': 13.75633,
            'default_lon': 100.50177
        },
        'electric_motorcycle': {
            'speed_limit_no_helmet': 25,
            'auto_limit_speed': True,
            'serial_port': '/dev/ttyUSB0',
            'baud_rate': 9600
        }
    }
    
    # สร้างและเริ่มต้นระบบ
    system = HelmetDetectionSystem(config)
    
    # เริ่มตรวจจับ
    system.run()


if __name__ == '__main__':
    main()
