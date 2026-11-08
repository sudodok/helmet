import cv2
import numpy as np
from collections import deque
import time
import json
from datetime import datetime
import os
import threading

# =====================================================
# ระบบตรวจจับหมวกกันน็อคสำหรับรถมอเตอร์ไซค์ไฟฟ้า
# Helmet Detection System for Electric Motorcycles
# (High-FPS Optimization Edition for Raspberry Pi & PC)
# =====================================================

# ตรวจสอบการใช้งานบนบอร์ด Raspberry Pi (GPIO & ARM)
try:
    import RPi.GPIO as GPIO
    RPI_AVAILABLE = True
except (ImportError, RuntimeError):
    RPI_AVAILABLE = False


class ThreadedCamera:
    """กล้องแยกเธรด (Non-blocking Threaded Video Capture)
    ดึงภาพจากกล้องใน Background Thread ตลอดเวลา ขจัดปัญหา Frame Lag และ I/O Blocking
    ช่วยให้ได้ FPS สูงสุดบน Raspberry Pi 4 / 5
    """
    def __init__(self, src=0, width=640, height=480, fps=30):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.ret, self.frame = self.cap.read()
        self.running = True
        self.lock = threading.Lock()
        if self.cap.isOpened():
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()

    def _capture_loop(self):
        while self.running:
            if not self.cap.isOpened():
                time.sleep(0.02)
                continue
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.ret = ret
                    self.frame = frame
            else:
                time.sleep(0.005)

    def read(self):
        with self.lock:
            if self.frame is not None:
                return self.ret, self.frame.copy()
            return False, None

    def isOpened(self):
        return self.cap.isOpened()

    def release(self):
        self.running = False
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=0.5)
        self.cap.release()


class HelmetDetectionSystem:
    """ระบบตรวจจับหมวกกันน็อคหลัก (High-FPS Architecture)"""
    
    def __init__(self, config=None):
        """เริ่มต้นระบบ"""
        self.config = config or self._default_config()
        self.detection_history = deque(maxlen=100)
        self.alert_log = []
        self.frame_count = 0
        self.start_time = time.time()
        
        self.current_speed = 0.0
        
        # สถานะหมวกนิรภัยล่าสุด
        self.last_helmet_status = True
        self.engine_started = False
        self.trip_start_time = None
        self.has_captured_start = False
        self.last_known_helmet_state = False

        # โหลดโมเดล YOLO (จัดลำดับ NCNN -> PyTorch .pt -> Darknet -> Demo)
        self._load_model()
        
        # สร้างโฟลเดอร์สำหรับบันทึก
        os.makedirs('logs', exist_ok=True)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.captures_dir = os.path.join(self.base_dir, 'captures')
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        os.makedirs(self.captures_dir, exist_ok=True)
        os.makedirs(os.path.join(self.captures_dir, 'safe_start'), exist_ok=True)
        os.makedirs(os.path.join(self.captures_dir, 'mid_ride_violations'), exist_ok=True)
        os.makedirs(os.path.join(self.captures_dir, 'no_helmet'), exist_ok=True)
        os.makedirs(os.path.join(self.captures_dir, 'manual_snapshots'), exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

        # เริ่มต้นส่ง Telemetry ไปยัง WebApp Server (localhost:5000)
        self._init_telemetry()

    def _init_telemetry(self):
        """เริ่มเธรดส่งข้อมูลข้อมูลสถานะความเร็วและความปลอดภัยไปยัง WebApp Server แบบ Real-time"""
        import urllib.request
        def telemetry_worker():
            while True:
                time.sleep(0.4)
                try:
                    payload = json.dumps({
                        'speed': self.current_speed,
                        'helmet': self.last_helmet_status,
                        'engine_locked': not self.engine_started,
                        'source': 'Raspberry Pi System'
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
        """ค่าตั้งต้นของระบบ ออกแบบเน้นความเร็วสูงสุด (High FPS) บน Raspberry Pi"""
        return {
            'model': {
                'confidence_threshold': 0.35,
                'nms_threshold': 0.4,
                'input_size': (320, 320)  # 320x320 ปรับเพื่อรีด FPS ให้สูงที่สุด
            },
            'camera': {
                'source': 0,
                'width': 640,
                'height': 480,
                'fps': 30
            },
            'performance': {
                'use_threaded_camera': True,   # กล้องแบบแยกเธรด
                'inference_interval': 2,       # สลับตรวจจับทุก 2 เฟรม (คงระดับ 30 FPS ไม่กระตุก)
                'imgsz': 320                  # ความละเอียดป้อน AI (320x320)
            },
            'detection': {
                'classes': ['with_helmet', 'without_helmet', 'helmet', 'no_helmet', 'person', 'motorcycle'],
                'colors': {
                    'with_helmet': (0, 255, 0),      # เขียว - สวมหมวก
                    'without_helmet': (0, 0, 255),    # แดง - ไม่สวมหมวก
                    'helmet': (0, 255, 0),          # เขียว
                    'no_helmet': (0, 0, 255),        # แดง
                    'person': (255, 255, 0),         # เหลือง - คน
                    'motorcycle': (255, 165, 0)      # ส้ม - มอเตอร์ไซค์
                }
            },
            'alert': {
                'enabled': True,
                'cooldown': 5,  # วินาที
                'capture_violation': True,
                'sound_alert': True
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
        """โหลดโมเดลตรวจจับ โดยค้นหาฟอร์แมต NCNN (เร็วที่สุดบน Pi) ก่อนเสมอ"""
        self.yolo_model = None
        self.model_loaded = False
        self.model_engine_name = "Demo"
        self.imgsz = self.config.get('performance', {}).get('imgsz', 320)
        self.inference_interval = self.config.get('performance', {}).get('inference_interval', 2)
        self.cached_detections = []
        self.fps_smooth = 0.0
        self.last_frame_time = time.time()
        self.inference_time_ms = 0.0

        base_dir = os.path.dirname(os.path.abspath(__file__))

        # 1. รายชื่อโฟลเดอร์โมเดล NCNN (เร็วที่สุดบน Raspberry Pi ARM CPU)
        ncnn_candidates = [
            os.path.join(base_dir, 'best_ncnn_model'),
            'best_ncnn_model',
            os.path.join(base_dir, 'helmet_ncnn_model'),
            'helmet_ncnn_model'
        ]

        # 2. รายชื่อไฟล์โมเดล PyTorch .pt
        pt_candidates = [
            os.path.join(base_dir, 'best.pt'),
            'best.pt',
            os.path.join(base_dir, 'helmet_yolov8n.pt'),
            'helmet_yolov8n.pt',
            os.path.join(base_dir, 'yolov8n.pt'),
            'yolov8n.pt'
        ]

        # พยายามโหลดผ่าน Ultralytics YOLO
        try:
            from ultralytics import YOLO

            # ลองโหลดแบบ NCNN ก่อน
            for ncnn_path in ncnn_candidates:
                if os.path.exists(ncnn_path) and os.path.isdir(ncnn_path):
                    self.yolo_model = YOLO(ncnn_path, task='detect')
                    self.model_loaded = True
                    self.model_engine_name = f"NCNN ARM ({self.imgsz}px)"
                    print(f"[INFO] 🚀 โหลดโมเดล NCNN สำหรับ Raspberry Pi สำเร็จ: {ncnn_path}")
                    return

            # หากไม่พบ NCNN ให้โหลด PyTorch .pt
            for pt_path in pt_candidates:
                if os.path.exists(pt_path):
                    self.yolo_model = YOLO(pt_path)
                    self.model_loaded = True
                    self.model_engine_name = f"YOLOv8 ({os.path.basename(pt_path)} {self.imgsz}px)"
                    print(f"[INFO] ⚡ โหลดโมเดล YOLOv8 สำเร็จ: {pt_path}")
                    return

        except Exception as e:
            print(f"[INFO] ไม่สามารถโหลด Ultralytics YOLO: {e}")

        # ลองโหลด Darknet เดิม (ถ้ามีไฟล์)
        model_cfg = self.config.get('model', {})
        if os.path.exists(model_cfg.get('weights', '')) and os.path.exists(model_cfg.get('config', '')):
            try:
                self.net = cv2.dnn.readNetFromDarknet(model_cfg['config'], model_cfg['weights'])
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                self.output_layers = self.net.getUnconnectedOutLayersNames()
                self.model_loaded = True
                self.model_engine_name = "Darknet YOLO"
                print("[INFO] โหลด Darknet YOLO สำเร็จ")
                return
            except Exception as e:
                print(f"[WARNING] ไม่สามารถโหลด Darknet: {e}")

        # สลับไปใช้ Demo Mode
        print("[WARNING] ไม่พบไฟล์โมเดล - ใช้โหมดจำลอง (Haar Cascade Demo Mode)")
        self.model_loaded = False
        self._setup_demo_mode()
    
    def _setup_demo_mode(self):
        """ตั้งค่าโหมดจำลองสำหรับทดสอบ"""
        self.net = None
        self.classes = self.config['detection']['classes']
        self.output_layers = []
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=True
        )
        print("[INFO] ใช้โหมดจำลอง (Demo Mode)")
    
    def detect_objects(self, frame):
        """ตรวจจับวัตถุในเฟรม รองรับโมเดลความเร็วสูง"""
        if self.model_loaded and self.yolo_model is not None:
            return self._detect_with_ultralytics(frame)
        elif self.model_loaded and hasattr(self, 'net') and self.net is not None:
            return self._detect_with_darknet(frame)
        else:
            return self._detect_demo_mode(frame)

    def _detect_with_ultralytics(self, frame):
        """ตรวจจับด้วย YOLOv8 / NCNN ด้วยขนาด imgsz=320 เพื่อ FPS สูงสุด"""
        detections = []
        conf_thresh = self.config['model'].get('confidence_threshold', 0.35)
        
        try:
            results = self.yolo_model(frame, imgsz=self.imgsz, verbose=False, conf=conf_thresh)[0]
            names_map = getattr(self.yolo_model, 'names', {})
            
            for box in results.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                x1, y1, x2, y2 = xyxy
                w = max(0, x2 - x1)
                h = max(0, y2 - y1)
                raw_name = names_map.get(cls_id, str(cls_id)).lower()

                # แปลงชื่อคลาสให้เข้ากับระบบ (รองรับ with_helmet / without_helmet และ helmet / no_helmet)
                if raw_name in ['with_helmet', 'helmet', 'hat']:
                    cls_name = 'with_helmet'
                elif raw_name in ['without_helmet', 'no_helmet', 'head', 'face']:
                    cls_name = 'without_helmet'
                elif raw_name in ['person', 'human']:
                    cls_name = 'person'
                elif raw_name in ['motorcycle', 'motor_bike', 'bicycle']:
                    cls_name = 'motorcycle'
                else:
                    cls_name = raw_name

                detections.append({
                    'class': cls_name,
                    'raw_name': raw_name,
                    'confidence': conf,
                    'box': [int(x1), int(y1), int(w), int(h)],
                    'class_id': cls_id
                })
        except Exception:
            pass
            
        return detections
    
    def _detect_with_darknet(self, frame):
        """ตรวจจับด้วย Darknet (Fallback)"""
        height, width = frame.shape[:2]
        input_size = self.config['model']['input_size']
        conf_threshold = self.config['model']['confidence_threshold']
        nms_threshold = self.config['model']['nms_threshold']
        
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, input_size, swapRB=True, crop=False)
        self.net.setInput(blob)
        outputs = self.net.forward(self.output_layers)
        
        boxes, confidences, class_ids = [], [], []
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
        
        indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)
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
        """ตรวจจับในโหมดจำลอง (Haar Cascade)"""
        detections = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        
        for (x, y, w, h) in faces:
            helmet_region_y = max(0, y - int(h * 0.8))
            helmet_region = gray[helmet_region_y:y, x:x+w]
            
            if helmet_region.size > 0:
                mean_val = np.mean(helmet_region)
                std_val = np.std(helmet_region)
                edges = cv2.Canny(helmet_region, 50, 150)
                edge_density = np.sum(edges > 0) / edges.size if edges.size > 0 else 0
                has_helmet = edge_density > 0.15 and std_val > 30
                
                if has_helmet:
                    detections.append({
                        'class': 'with_helmet',
                        'confidence': min(0.7 + edge_density, 0.95),
                        'box': [x, helmet_region_y, w, y - helmet_region_y + h],
                        'class_id': 0
                    })
                else:
                    detections.append({
                        'class': 'without_helmet',
                        'confidence': 0.6,
                        'box': [x, y, w, h],
                        'class_id': 1
                    })
            
            detections.append({
                'class': 'person',
                'confidence': 0.8,
                'box': [x - 20, y - 10, w + 40, h + 100],
                'class_id': 2
            })
        
        fg_mask = self.bg_subtractor.apply(frame)
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            if cv2.contourArea(contour) > 5000:
                x, y, w, h = cv2.boundingRect(contour)
                if 0.5 < (w / h) < 3.0:
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
            
            # ป้ายข้อความ
            display_name = "HELMET" if cls in ['with_helmet', 'helmet'] else ("NO HELMET" if cls in ['without_helmet', 'no_helmet'] else cls.upper())
            label = f"{display_name} {conf:.2f}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            
            cv2.rectangle(frame, (x, max(0, y - label_size[1] - 8)), (x + label_size[0] + 6, max(0, y)), color, -1)
            cv2.putText(frame, label, (x + 3, max(label_size[1], y - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            
            # ตรวจสอบการละเมิด
            if cls in ['without_helmet', 'no_helmet']:
                violation_detected = True
                self._draw_warning(frame, x, y, w, h)
        
        return frame, violation_detected
    
    def _draw_warning(self, frame, x, y, w, h):
        """วาดคำเตือนสำหรับการไม่สวมหมวก"""
        if int(time.time() * 3) % 2 == 0:
            cv2.rectangle(frame, (x - 5, y - 5), (x + w + 5, y + h + 5), (0, 0, 255), 3)
        
        warning_text = "WARNING: NO HELMET!"
        text_size = cv2.getTextSize(warning_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        text_x = x + (w - text_size[0]) // 2
        text_y = y + h + 30
        
        cv2.rectangle(frame, (text_x - 5, text_y - text_size[1] - 5), (text_x + text_size[0] + 5, text_y + 5), (0, 0, 255), -1)
        cv2.putText(frame, warning_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    def draw_dashboard(self, frame):
        """วาด Dashboard แสดงสถานะ, FPS สด, และ Engine ที่ใช้งาน"""
        height, width = frame.shape[:2]
        now = time.time()
        now_time_str = datetime.now().strftime('%H:%M:%S')

        if self.engine_started and self.trip_start_time is not None:
            trip_sec = int(now - self.trip_start_time)
            hrs, rem = divmod(trip_sec, 3600)
            mins, secs = divmod(rem, 60)
            stopwatch_display = f"{hrs:02d}:{mins:02d}:{secs:02d}"
            timer_label = "RIDING"
            timer_color = (0, 255, 0)
        else:
            stopwatch_display = "00:00:00"
            timer_label = "STANDBY"
            timer_color = (180, 180, 180)

        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 50), (420, 250), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        cv2.putText(frame, "HELMET SAFETY SYSTEM", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 255, 255), 2)
        cv2.line(frame, (20, 84), (410, 84), (0, 255, 255), 1)

        engine_status = "STARTED (READY)" if self.engine_started else "LOCKED (OFF)"
        fps_text = f"FPS: {self.fps_smooth:.1f} ({self.inference_time_ms:.0f}ms)"
        info_lines = [
            (f"{fps_text} | {self.model_engine_name}", (0, 255, 200)),
            (f"Clock Time: {now_time_str}", (255, 255, 255)),
            (f"Stopwatch ({timer_label}): {stopwatch_display}", timer_color),
            (f"Engine: {engine_status}", (0, 255, 0) if self.engine_started else (0, 0, 255)),
            (f"Speed: {self.current_speed:.1f} km/h", (100, 240, 255)),
            (f"Violations: {len(self.alert_log)}", (255, 180, 0))
        ]

        for i, (line, col) in enumerate(info_lines):
            cv2.putText(frame, line, (20, 108 + i * 22), cv2.FONT_HERSHEY_SIMPLEX, 0.46, col, 1)

        return frame
    
    def process_violation(self, frame, detections):
        """บันทึกข้อมูลและภาพถ่ายหลักฐานการละเมิด"""
        timestamp = datetime.now()
        speed = self.current_speed
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
            'speed_kmh': speed,
            'detections': [{
                'class': d['class'],
                'confidence': d['confidence'],
                'box': d['box']
            } for d in detections if d['class'] in ['without_helmet', 'no_helmet']]
        }

        self.alert_log.append(violation)
        self._save_log(violation)

        if self.config['alert']['capture_violation']:
            filename = self.capture_violation_image(frame, violation_type, detections, trip_str)
            violation['image_file'] = filename

        # ส่งสัญญาณแจ้งเตือนฮาร์ดแวร์
        if hasattr(self, 'controller') and self.controller:
            self.controller.alert_violation(is_mid_ride=is_mid_ride)

        self._send_speed_limit_command()

    def capture_violation_image(self, frame, violation_type, detections, trip_str):
        """บันทึกภาพหลักฐานพร้อมลายน้ำ"""
        timestamp = datetime.now()
        folder = 'mid_ride_violations' if violation_type == "MID_RIDE_HELMET_REMOVAL" else 'no_helmet'
        file_prefix = 'mid_ride' if violation_type == "MID_RIDE_HELMET_REMOVAL" else 'no_helmet'
        filename = os.path.join(self.captures_dir, folder, f"{file_prefix}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg")

        annotated_frame, _ = self.draw_detections(frame.copy(), detections)
        h, w = annotated_frame.shape[:2]

        cv2.rectangle(annotated_frame, (0, h - 45), (w, h), (15, 15, 15), -1)
        cv2.rectangle(annotated_frame, (0, h - 45), (w, h - 43), (0, 0, 255), -1)

        dur_text = f"TRIP: {trip_str}" if violation_type == "MID_RIDE_HELMET_REMOVAL" else "PRE-START: 00m 00s"
        watermark_text = f"[VIOLATION] {violation_type} | {dur_text} | SPEED: {self.current_speed:.1f} km/h | TIME: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        cv2.putText(annotated_frame, watermark_text, (12, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 255), 1)

        cv2.imwrite(filename, annotated_frame)
        print(f"[CAPTURE] 🔴 บันทึกภาพหลักฐาน: {filename}")
        return filename

    def capture_start_verified(self, frame, detections):
        """บันทึกภาพยืนยันการสวมหมวกออกรถครั้งแรก"""
        timestamp = datetime.now()
        filename = os.path.join(self.captures_dir, 'safe_start', f"start_verified_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg")
        annotated_frame, _ = self.draw_detections(frame.copy(), detections)
        h, w = annotated_frame.shape[:2]

        cv2.rectangle(annotated_frame, (0, h - 45), (w, h), (15, 15, 15), -1)
        cv2.rectangle(annotated_frame, (0, h - 45), (w, h - 43), (0, 200, 0), -1)
        watermark_text = f"[PASS] SAFE START | HELMET VERIFIED | STOPWATCH: 00m 00s | SPEED: {self.current_speed:.1f} km/h | TIME: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        cv2.putText(annotated_frame, watermark_text, (12, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 255), 1)

        cv2.imwrite(filename, annotated_frame)
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
            logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            logs.append(violation)
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] ไม่สามารถบันทึก log: {e}")
    
    def run(self, source=None):
        """เริ่มต้นระบบตรวจจับ (High-FPS Real-time Loop)"""
        source = source or self.config['camera']['source']
        
        print("=" * 65)
        print(" 🛵 ระบบตรวจจับหมวกกันน็อค - High FPS Edition (Raspberry Pi & PC)")
        print("=" * 65)
        print(f" แหล่งวิดีโอ: {source}")
        print(f" สถาปัตยกรรมโมเดล: {self.model_engine_name}")
        print(f" ความละเอียดป้อน AI: {self.imgsz}x{self.imgsz}")
        print(f" อัตราสลับตรวจจับ: ทุกๆ {self.inference_interval} เฟรม")
        print("=" * 65)
        print(" กด 'q' เพื่อออก | 's' เพื่อบันทึกภาพ | 'r' เพื่อรีเซ็ต")
        print("=" * 65)
        
        motor_cfg = self.config.get('electric_motorcycle', {})
        self.controller = ElectricMotorcycleController(
            port=motor_cfg.get('serial_port'),
            baud_rate=motor_cfg.get('baud_rate', 9600),
            gpio_config=motor_cfg.get('gpio_pins')
        )
        self.controller.connect()
        
        # เลือกเปิดกล้องแบบ Threaded เพื่อรีด FPS สูงสุด
        use_threaded = self.config.get('performance', {}).get('use_threaded_camera', True)
        if use_threaded:
            cap = ThreadedCamera(
                src=source,
                width=self.config['camera']['width'],
                height=self.config['camera']['height'],
                fps=self.config['camera']['fps']
            )
        else:
            cap = cv2.VideoCapture(source)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config['camera']['width'])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config['camera']['height'])
        
        if not cap.isOpened():
            print("[ERROR] ไม่สามารถเปิดกล้องได้")
            return
        
        last_alert_time = 0
        self.last_frame_time = time.time()
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.005)
                    continue
                
                self.frame_count += 1
                
                # คำนวณ Instantaneous FPS (Exponential Moving Average)
                now_t = time.time()
                dt = now_t - self.last_frame_time
                self.last_frame_time = now_t
                if dt > 0:
                    inst_fps = 1.0 / dt
                    self.fps_smooth = 0.9 * self.fps_smooth + 0.1 * inst_fps if self.fps_smooth > 0 else inst_fps
                
                # เทคนิคข้ามเฟรม (Frame Skipping): สลับรัน AI ทุก N เฟรม รักษาอัตรา 30 FPS ไม่กระตุก
                if self.frame_count % self.inference_interval == 0:
                    t_infer_start = time.time()
                    detections = self.detect_objects(frame)
                    self.inference_time_ms = (time.time() - t_infer_start) * 1000
                    self.cached_detections = detections
                else:
                    detections = self.cached_detections

                self.detection_history.extend(detections)
                
                # วาดผลการตรวจจับ
                frame, violation = self.draw_detections(frame, detections)
                self.last_helmet_status = not violation
                
                # วาด Dashboard
                frame = self.draw_dashboard(frame)
                
                # จัดการบันทึกภาพตามเหตุการณ์
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
                        
                        h, w = frame.shape[:2]
                        cv2.putText(
                            frame, "! HELMET REQUIRED !",
                            (w // 2 - 200, h - 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2,
                            (0, 0, 255), 3
                        )
                
                # แสดงผลหน้าต่างตรวจจับ
                cv2.imshow('Helmet Detection System', frame)
                key = cv2.waitKey(1) & 0xFF

                try:
                    if self.frame_count > 10 and cv2.getWindowProperty('Helmet Detection System', cv2.WND_PROP_VISIBLE) < 1:
                        print("[INFO] ผู้ใช้ปิดหน้าต่างโปรแกรม")
                        break
                except Exception:
                    pass
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
                    watermark_text = f"MANUAL SNAPSHOT | {status_text} | STOPWATCH: {dur_str} | SPEED: {self.current_speed:.1f} km/h | TIME: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                    cv2.putText(annotated_frame, watermark_text, (12, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 255), 1)

                    cv2.imwrite(filename, annotated_frame)
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
        """สร้างรายงานสรุปหลังปิดโปรแกรม"""
        elapsed = time.time() - self.start_time
        report = {
            'summary': {
                'total_frames': self.frame_count,
                'runtime_seconds': round(elapsed, 2),
                'average_fps': round(self.frame_count / elapsed, 2) if elapsed > 0 else 0,
                'total_violations': len(self.alert_log),
                'mode': self.model_engine_name,
                'speed_kmh': self.current_speed
            },
            'violations': self.alert_log
        }
        report_file = f"logs/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print("\n" + "=" * 60)
        print(" รายงานสรุป")
        print("=" * 60)
        print(f" จำนวนเฟรม: {report['summary']['total_frames']}")
        print(f" เวลาทำงาน: {report['summary']['runtime_seconds']} วินาที")
        print(f" FPS เฉลี่ย: {report['summary']['average_fps']}")
        print(f" การละเมิดทั้งหมด: {report['summary']['total_violations']}")
        print(f" โหมดการประมวลผล: {self.model_engine_name}")
        print(f" รายงานบันทึกที่: {report_file}")
        print("=" * 60)


class ElectricMotorcycleController:
    """ตัวควบคุมรถมอเตอร์ไซค์ไฟฟ้าจริง (รองรับทั้ง Raspberry Pi 4 GPIO และ Serial เชื่อมต่อ Arduino)"""
    
    def __init__(self, port=None, baud_rate=9600, gpio_config=None):
        self.port = port or ('/dev/ttyAMA0' if RPI_AVAILABLE else '/dev/ttyUSB0')
        self.baud_rate = baud_rate
        self.current_speed_limit = None
        self.is_connected = False
        self.helmet_status = 'unknown'
        self.serial = None
        
        self.gpio_cfg = gpio_config or {
            'relay': 17,     # สั่ง Relay ดึงสาย Speed Limit / Throttle
            'buzzer': 27,    # สัญญาณเสียงเตือน Buzzer
            'led_green': 22, # ไฟเขียว: สวมหมวก (ปลอดภัย)
            'led_red': 23    # ไฟแดง: ไม่สวมหมวก (อันตราย)
        }
        
    def connect(self):
        """เริ่มต้นการเชื่อมต่อฮาร์ดแวร์บน Raspberry Pi 4 หรือ Serial"""
        if RPI_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                for pin_name, pin_num in self.gpio_cfg.items():
                    GPIO.setup(pin_num, GPIO.OUT)
                    GPIO.output(pin_num, GPIO.LOW)
                print("[GPIO] ตั้งค่าพิน Raspberry Pi 4 GPIO สำเร็จ (Relay, Buzzer, LEDs)")
            except Exception as e:
                print(f"[GPIO Warning]: {e}")
        
        try:
            import serial
            self.serial = serial.Serial(
                self.port, 
                self.baud_rate, 
                timeout=1
            )
            self.is_connected = True
            print(f"[HARDWARE] เชื่อมต่อพอร์ต {self.port} สำเร็จ")
        except Exception as e:
            if not RPI_AVAILABLE:
                print(f"[HARDWARE] จำลองการทำงาน (ไม่พบพอร์ต Serial: {e})")
            else:
                print(f"[HARDWARE Warning] พอร์ต Serial ไม่พร้อมใช้งาน: {e}")
            self.is_connected = False
    
    def set_speed_limit(self, max_speed):
        """ตั้งค่าจำกัดความเร็ว"""
        self.current_speed_limit = max_speed
        
        if RPI_AVAILABLE:
            try:
                GPIO.output(self.gpio_cfg['relay'], GPIO.HIGH)
                print(f"[GPIO] เปิด Relay จำกัดความเร็วรถ (ดึงสาย Speed Limit)")
            except Exception as e:
                print(f"[GPIO Error]: {e}")
                
        if self.is_connected and self.serial:
            try:
                command = f"SPEED_LIMIT:{max_speed}\n"
                self.serial.write(command.encode())
                print(f"[MOTOR] จำกัดความเร็วที่ {max_speed} km/h")
            except Exception as e:
                print(f"[MOTOR SERIAL Error]: {e}")
        elif not RPI_AVAILABLE:
            print(f"[SIM] จำลองจำกัดความเร็วรถ: {max_speed} km/h")
    
    def remove_speed_limit(self):
        """ยกเลิกการจำกัดความเร็ว"""
        self.current_speed_limit = None
        
        if RPI_AVAILABLE:
            try:
                GPIO.output(self.gpio_cfg['relay'], GPIO.LOW)
                print(f"[GPIO] ปิด Relay ยกเลิกการจำกัดความเร็ว (ความเร็วปกติ)")
            except Exception as e:
                print(f"[GPIO Error]: {e}")
                
        if self.is_connected and self.serial:
            try:
                command = "SPEED_LIMIT:NONE\n"
                self.serial.write(command.encode())
                print("[MOTOR] ยกเลิกการจำกัดความเร็ว")
            except Exception as e:
                print(f"[MOTOR SERIAL Error]: {e}")
        elif not RPI_AVAILABLE:
            print("[SIM] ยกเลิกจำกัดความเร็ว (Normal Speed)")
    
    def alert_violation(self, is_mid_ride=False):
        """ส่งสัญญาณเตือนฮาร์ดแวร์จริง (ไฟแดง + เสียง Buzzer)
        ตามโจทย์ความปลอดภัย: กรณีถอดหมวกกลางคัน จะส่งเสียงเตือนและเปิดไฟเตือนทันที
        โดยไม่สั่งกระตุกหรือตัดความเร็วกะทันหันเพื่อความปลอดภัยของผู้ขับขี่
        """
        if RPI_AVAILABLE:
            def hardware_alert_worker():
                try:
                    # 1. เปิดไฟแดง และดับไฟเขียว
                    GPIO.output(self.gpio_cfg['led_green'], GPIO.LOW)
                    GPIO.output(self.gpio_cfg['led_red'], GPIO.HIGH)
                    
                    # 2. ส่งเสียง Buzzer เตือนเป็นจังหวะ
                    # ถ้าเป็นการถอดหมวกกลางคัน จะเตือนเป็นจังหวะถี่และยาวขึ้น
                    beep_times = 5 if is_mid_ride else 3
                    beep_interval = 0.15 if is_mid_ride else 0.25
                    
                    for _ in range(beep_times):
                        GPIO.output(self.gpio_cfg['buzzer'], GPIO.HIGH)
                        time.sleep(beep_interval)
                        GPIO.output(self.gpio_cfg['buzzer'], GPIO.LOW)
                        time.sleep(beep_interval)
                        
                except Exception as e:
                    print(f"[GPIO Alert Error]: {e}")
                    
            threading.Thread(target=hardware_alert_worker, daemon=True).start()
            
        print(f"[HARDWARE ALERT] 🚨 ส่งสัญญาณเตือนฮาร์ดแวร์ (LED Red + Buzzer Beep) | โหมด: {'ถอดหมวกกลางคัน' if is_mid_ride else 'ไม่สวมหมวกก่อนออกรถ'}")



    def disconnect(self):
        """ตัดการเชื่อมต่อและคืนค่าพิน GPIO ปลอดภัย"""
        if RPI_AVAILABLE:
            try:
                GPIO.output(self.gpio_cfg['relay'], GPIO.LOW)
                GPIO.output(self.gpio_cfg['buzzer'], GPIO.LOW)
                GPIO.output(self.gpio_cfg['led_red'], GPIO.LOW)
                GPIO.output(self.gpio_cfg['led_green'], GPIO.LOW)
                GPIO.cleanup()
                print("[GPIO] คืนค่า GPIO บน Raspberry Pi 4 สำเร็จ")
            except Exception as e:
                print(f"[GPIO Cleanup Error]: {e}")
                
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
                print("[HARDWARE] ปิดพอร์ต Serial สำเร็จ")
            except Exception:
                pass


if __name__ == '__main__':
    system = HelmetDetectionSystem()
    system.run()
