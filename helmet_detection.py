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
        
        # โหลด YOLO model
        self._load_model()
        
        # สร้างโฟลเดอร์สำหรับบันทึก
        os.makedirs('logs', exist_ok=True)
        os.makedirs('captures', exist_ok=True)
        
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
            'electric_motorcycle': {
                'speed_limit_no_helmet': 25,  # km/h
                'auto_limit_speed': True,
                'serial_port': '/dev/ttyUSB0',
                'baud_rate': 9600
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
        """วาด Dashboard แสดงสถานะ"""
        height, width = frame.shape[:2]
        
        # พื้นหลัง Dashboard
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (350, 200), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # หัวข้อ
        cv2.putText(
            frame, "Helmet Detection System", (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2
        )
        cv2.line(frame, (20, 50), (340, 50), (0, 255, 255), 1)
        
        # ข้อมูล
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        info_lines = [
            f"FPS: {fps:.1f}",
            f"Frame: {self.frame_count}",
            f"Detections: {len(self.detection_history)}",
            f"Violations: {len(self.alert_log)}",
            f"Mode: {'YOLO' if self.model_loaded else 'Demo'}",
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        ]
        
        for i, line in enumerate(info_lines):
            cv2.putText(
                frame, line, (20, 75 + i * 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
            )
        
        return frame
    
    def process_violation(self, frame, detections):
        """จัดการเมื่อพบการละเมิด"""
        timestamp = datetime.now()
        
        violation = {
            'timestamp': timestamp.isoformat(),
            'frame_number': self.frame_count,
            'detections': [{
                'class': d['class'],
                'confidence': d['confidence'],
                'box': d['box']
            } for d in detections if d['class'] == 'no_helmet']
        }
        
        self.alert_log.append(violation)
        
        # บันทึกภาพ
        if self.config['alert']['capture_violation']:
            filename = f"captures/violation_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(filename, frame)
            violation['image'] = filename
            print(f"[ALERT] บันทึกภาพการละเมิด: {filename}")
        
        # ส่งสัญญาณจำกัดความเร็ว
        if self.config['electric_motorcycle']['auto_limit_speed']:
            self._send_speed_limit_command()
        
        # บันทึก log
        self._save_log(violation)
        
        return violation
    
    def _send_speed_limit_command(self):
        """ส่งคำสั่งจำกัดความเร็วไปยังตัวควบคุมมอเตอร์"""
        speed_limit = self.config['electric_motorcycle']['speed_limit_no_helmet']
        
        try:
            import serial
            port = self.config['electric_motorcycle']['serial_port']
            baud = self.config['electric_motorcycle']['baud_rate']
            
            command = json.dumps({
                'action': 'limit_speed',
                'max_speed': speed_limit,
                'reason': 'no_helmet_detected'
            })
            
            with serial.Serial(port, baud, timeout=1) as ser:
                ser.write(command.encode())
                ser.write(b'\n')
                print(f"[MOTOR] จำกัดความเร็ว: {speed_limit} km/h")
                
        except ImportError:
            print(f"[SIM] จำลองจำกัดความเร็ว: {speed_limit} km/h")
        except Exception as e:
            print(f"[ERROR] ไม่สามารถส่งคำสั่ง: {e}")
    
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
        print("=" * 60)
        print(" กด 'q' เพื่อออก | 's' เพื่อบันทึกภาพ | 'r' เพื่อรีเซ็ต")
        print("=" * 60)
        
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
                
                # ตรวจจับวัตถุ
                detections = self.detect_objects(frame)
                self.detection_history.extend(detections)
                
                # วาดผลการตรวจจับ
                frame, violation = self.draw_detections(frame, detections)
                
                # วาด Dashboard
                frame = self.draw_dashboard(frame)
                
                # จัดการการละเมิด
                if violation:
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
                
                # จัดการ keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    filename = f"captures/manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"[SAVE] บันทึกภาพ: {filename}")
                elif key == ord('r'):
                    self.detection_history.clear()
                    self.alert_log.clear()
                    self.frame_count = 0
                    self.start_time = time.time()
                    print("[RESET] รีเซ็ตระบบ")
                    
        except KeyboardInterrupt:
            print("\n[INFO] หยุดระบบ...")
        finally:
            cap.release()
            cv2.destroyAllWindows()
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
                'mode': 'YOLO' if self.model_loaded else 'Demo'
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
        print(f" รายงานบันทึกที่: {report_file}")
        print("=" * 60)


class ElectricMotorcycleController:
    """ตัวควบคุมรถมอเตอร์ไซค์ไฟฟ้า"""
    
    def __init__(self, port='/dev/ttyUSB0', baud_rate=9600):
        self.port = port
        self.baud_rate = baud_rate
        self.current_speed_limit = None
        self.is_connected = False
        self.helmet_status = 'unknown'
        
    def connect(self):
        """เชื่อมต่อกับตัวควบคุมมอเตอร์"""
        try:
            import serial
            self.serial = serial.Serial(
                self.port, self.baud_rate, timeout=1
            )
            self.is_connected = True
            print(f"[MOTOR] เชื่อมต่อที่ {self.port}")
        except Exception as e:
            print(f"[MOTOR] ไม่สามารถเชื่อมต่อ: {e}")
            self.is_connected = False
    
    def set_speed_limit(self, max_speed):
        """ตั้งค่าจำกัดความเร็ว"""
        self.current_speed_limit = max_speed
        command = f"SPEED_LIMIT:{max_speed}\n"
        
        if self.is_connected:
            try:
                self.serial.write(command.encode())
                print(f"[MOTOR] จำกัดความเร็ว: {max_speed} km/h")
            except Exception as e:
                print(f"[MOTOR] Error: {e}")
        else:
            print(f"[SIM] จำกัดความเร็ว: {max_speed} km/h")
    
    def remove_speed_limit(self):
        """ยกเลิกการจำกัดความเร็ว"""
        self.current_speed_limit = None
        command = "SPEED_LIMIT:NONE\n"
        
        if self.is_connected:
            try:
                self.serial.write(command.encode())
                print("[MOTOR] ยกเลิกจำกัดความเร็ว")
            except Exception as e:
                print(f"[MOTOR] Error: {e}")
        else:
            print("[SIM] ยกเลิกจำกัดความเร็ว")
    
    def update_helmet_status(self, status):
        """อัปเดตสถานะหมวกกันน็อค"""
        self.helmet_status = status
        
        if status == 'no_helmet':
            self.set_speed_limit(25)  # จำกัดที่ 25 km/h
        elif status == 'helmet':
            self.remove_speed_limit()
    
    def disconnect(self):
        """ตัดการเชื่อมต่อ"""
        if self.is_connected:
            try:
                self.serial.close()
                print("[MOTOR] ตัดการเชื่อมต่อ")
            except:
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
