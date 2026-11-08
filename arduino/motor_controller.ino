// =====================================================
// Helmet Detection - Motor & Safety Interlock Controller
// สำหรับ Arduino Uno / Nano / ESP32
// รองรับ: ควบคุมความเร็วมอเตอร์ + สัญญาณเตือน Buzzer + ไฟ LED เขียว/แดง
// =====================================================

// กำหนด Pin สำหรับควบคุมมอเตอร์และสัญญาณเตือน
const int MOTOR_PWM_PIN = 9;   // ขา PWM คุมสปีดมอเตอร์
const int BUZZER_PIN    = 8;   // ขา Buzzer สัญญาณเตือน
const int LED_GREEN     = 7;   // ขา LED เขียว (สวมหมวก / ปลอดภัย)
const int LED_RED       = 6;   // ขา LED แดง (ไม่สวมหมวก / อันตราย)

// ตัวแปรสถานะ
int maxSpeed = 255;            // PWM สูงสุด (0-255)
bool helmetDetected = true;    // สถานะหมวก
int currentSpeed = 0;          // ความเร็วปัจจุบัน

void setup() {
  // สื่อสารกับคอมพิวเตอร์ / Raspberry Pi ผ่าน USB Serial
  Serial.begin(9600);
  
  pinMode(MOTOR_PWM_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  
  // เริ่มต้นสถานะพร้อมใช้งาน
  digitalWrite(LED_GREEN, HIGH);
  digitalWrite(LED_RED, LOW);
  analogWrite(MOTOR_PWM_PIN, maxSpeed);
  
  Serial.println("[SYSTEM] Motor & Safety Interlock Controller Ready");
}

void loop() {
  // 1. รับคำสั่งควบคุมจากคอมพิวเตอร์ / Raspberry Pi
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    processCommand(command);
  }
  
  // 2. ควบคุมความเร็วมอเตอร์ตามขีดจำกัด
  int limitedSpeed = map(currentSpeed, 0, 255, 0, maxSpeed);
  analogWrite(MOTOR_PWM_PIN, limitedSpeed);
  
  // 3. แสดงผล LED และเสียงเตือน
  if (helmetDetected) {
    digitalWrite(LED_GREEN, HIGH);
    digitalWrite(LED_RED, LOW);
  } else {
    digitalWrite(LED_GREEN, LOW);
    digitalWrite(LED_RED, HIGH);
    
    // เสียง Buzzer เตือนเป็นจังหวะทุกๆ 2 วินาที
    if (millis() % 2000 < 150) {
      tone(BUZZER_PIN, 1200, 150);
    }
  }
  
  delay(10);
}

// ประมวลผลคำสั่งจากคอมพิวเตอร์
void processCommand(String cmd) {
  if (cmd.startsWith("SPEED_LIMIT:")) {
    String value = cmd.substring(12);
    
    if (value == "NONE") {
      maxSpeed = 255; // ความเร็วเต็มพิกัด
      helmetDetected = true;
      Serial.println("[MOTOR] Speed limit removed");
    } else {
      int limitKmh = value.toInt();
      // แปลงความเร็ว km/h เป็นค่า PWM (0-255) โดยสมมุติความเร็วสูงสุด 60 km/h
      maxSpeed = map(constrain(limitKmh, 0, 60), 0, 60, 0, 255);
      helmetDetected = false;
      Serial.print("[MOTOR] Speed limited to ");
      Serial.print(limitKmh);
      Serial.println(" km/h");
    }
  } else if (cmd == "STATUS:HELMET_ON") {
    helmetDetected = true;
    Serial.println("[STATUS] Helmet detected");
  } else if (cmd == "STATUS:NO_HELMET") {
    helmetDetected = false;
    Serial.println("[STATUS] No helmet - Warning active");
  } else if (cmd.startsWith("SET_SPEED:")) {
    currentSpeed = cmd.substring(10).toInt();
    currentSpeed = constrain(currentSpeed, 0, 255);
  }
}
