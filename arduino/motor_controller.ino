// =====================================================
// Helmet Detection - Motor Controller with GPS ATGM336H
// สำหรับ Arduino Uno / Nano / ESP32
// รองรับ: ควบคุมความเร็วมอเตอร์ + สัญญาณเตือน + GPS ATGM336H (NEO-M8N)
// =====================================================

#include <SoftwareSerial.h>

// กำหนด Pin สำหรับควบคุมมอเตอร์และสัญญาณเตือน
const int MOTOR_PWM_PIN = 9;   // ขา PWM คุมสปีดมอเตอร์
const int BUZZER_PIN    = 8;   // ขา Buzzer สัญญาณเตือน
const int LED_GREEN     = 7;   // ขา LED เขียว (สวมหมวก / ปลอดภัย)
const int LED_RED       = 6;   // ขา LED แดง (ไม่สวมหมวก / อันตราย)

// กำหนด Pin สำหรับโมดูล GPS ATGM336H / NEO-M8N
// ต่อ TXD ของ GPS -> Pin 4 (Arduino RX)
// ต่อ RXD ของ GPS -> Pin 3 (Arduino TX)
const int GPS_RX_PIN = 4;
const int GPS_TX_PIN = 3;
SoftwareSerial gpsSerial(GPS_RX_PIN, GPS_TX_PIN);

// ตัวแปรสถานะ
int maxSpeed = 255;            // PWM สูงสุด (0-255)
bool helmetDetected = true;    // สถานะหมวก
int currentSpeed = 0;          // ความเร็วปัจจุบัน

// ตัวแปรข้อมูล GPS
float gpsLatitude = 0.0;
float gpsLongitude = 0.0;
float gpsSpeedKmh = 0.0;
int gpsSatellites = 0;
bool gpsHasFix = false;

// ตัวแปรจับเวลาส่งข้อมูล GPS ขึ้นคอมพิวเตอร์
unsigned long lastGpsReport = 0;
const unsigned long GPS_REPORT_INTERVAL = 1000; // ส่งทุกๆ 1 วินาที

void setup() {
  // สื่อสารกับคอมพิวเตอร์ผ่าน USB Serial
  Serial.begin(9600);
  
  // สื่อสารกับโมดูล GPS ATGM336H
  gpsSerial.begin(9600);
  
  pinMode(MOTOR_PWM_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  
  // เริ่มต้นสถานะพร้อมใช้งาน
  digitalWrite(LED_GREEN, HIGH);
  digitalWrite(LED_RED, LOW);
  analogWrite(MOTOR_PWM_PIN, maxSpeed);
  
  Serial.println("[SYSTEM] Motor Controller with ATGM336H GPS Ready");
}

void loop() {
  // 1. อ่านข้อมูลจาก GPS ATGM336H
  readGpsData();
  
  // 2. รับคำสั่งควบคุมจากคอมพิวเตอร์ (Python)
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    processCommand(command);
  }
  
  // 3. ควบคุมความเร็วมอเตอร์ตามขีดจำกัด
  int limitedSpeed = map(currentSpeed, 0, 255, 0, maxSpeed);
  analogWrite(MOTOR_PWM_PIN, limitedSpeed);
  
  // 4. แสดงผล LED และเสียงเตือน
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
  
  // 5. ส่งพิกัด GPS กลับไปยังคอมพิวเตอร์เป็นระยะ
  if (millis() - lastGpsReport >= GPS_REPORT_INTERVAL) {
    sendGpsReport();
    lastGpsReport = millis();
  }
  
  delay(10);
}

// ประมวลผลคำสั่งจากคอมพิวเตอร์
void processCommand(String cmd) {
  if (cmd.startsWith("SPEED_LIMIT:")) {
    String value = cmd.substring(12);
    
    if (value == "NONE") {
      maxSpeed = 255;
      helmetDetected = true;
      Serial.println("[MOTOR] Speed limit removed (Helmet OK)");
    } else {
      int speedKmh = value.toInt();
      // แปลงความเร็ว 0-80 km/h เป็น PWM 0-255
      maxSpeed = map(speedKmh, 0, 80, 0, 255);
      helmetDetected = false;
      Serial.print("[MOTOR] Speed limited to: ");
      Serial.print(speedKmh);
      Serial.println(" km/h (Violation Alert)");
    }
  } else if (cmd == "GET_GPS") {
    sendGpsReport();
  }
}

// ส่งพิกัด GPS ไปยังคอมพิวเตอร์ในฟอร์แมต: GPS:lat,lon,speed,sats,fix
void sendGpsReport() {
  Serial.print("GPS:");
  Serial.print(gpsLatitude, 6);
  Serial.print(",");
  Serial.print(gpsLongitude, 6);
  Serial.print(",");
  Serial.print(gpsSpeedKmh, 1);
  Serial.print(",");
  Serial.print(gpsSatellites);
  Serial.print(",");
  Serial.println(gpsHasFix ? "1" : "0");
}

// อ่านและแยกข้อมูล NMEA จากโมดูล ATGM336H / NEO-M8N
void readGpsData() {
  while (gpsSerial.available() > 0) {
    String nmea = gpsSerial.readStringUntil('\n');
    nmea.trim();
    
    // ตรวจสอบประโยค $GNRMC หรือ $GPRMC (มีพิกัดและความเร็ว)
    if (nmea.startsWith("$GNRMC") || nmea.startsWith("$GPRMC")) {
      parseRMC(nmea);
    } 
    // ตรวจสอบประโยค $GNGGA หรือ $GPGGA (มีจำนวนดาวเทียม)
    else if (nmea.startsWith("$GNGGA") || nmea.startsWith("$GPGGA")) {
      parseGGA(nmea);
    }
  }
}

// แยกข้อมูลจาก $GNRMC / $GPRMC
void parseRMC(String rmc) {
  // ฟอร์แมต: $GNRMC,time,status,lat,N/S,lon,E/W,speed_knots,angle,date,...
  int index = 0;
  String fields[13];
  int from = 0;
  
  for (int i = 0; i < rmc.length() && index < 13; i++) {
    if (rmc.charAt(i) == ',' || i == rmc.length() - 1) {
      fields[index++] = rmc.substring(from, i);
      from = i + 1;
    }
  }
  
  if (index >= 8) {
    // fields[2] = 'A' หมายถึงจับสัญญาณดาวเทียมได้ (Valid)
    if (fields[2] == "A") {
      gpsHasFix = true;
      
      // แปลงพิกัด Latitude (ddmm.mmmm) เป็น Decimal Degrees
      float rawLat = fields[3].toFloat();
      int latDeg = int(rawLat / 100);
      float latMin = rawLat - (latDeg * 100);
      gpsLatitude = latDeg + (latMin / 60.0);
      if (fields[4] == "S") gpsLatitude = -gpsLatitude;
      
      // แปลงพิกัด Longitude (dddmm.mmmm) เป็น Decimal Degrees
      float rawLon = fields[5].toFloat();
      int lonDeg = int(rawLon / 100);
      float lonMin = rawLon - (lonDeg * 100);
      gpsLongitude = lonDeg + (lonMin / 60.0);
      if (fields[6] == "W") gpsLongitude = -gpsLongitude;
      
      // แปลงความเร็วจาก Knots เป็น km/h (1 knot = 1.852 km/h)
      float speedKnots = fields[7].toFloat();
      gpsSpeedKmh = speedKnots * 1.852;
    } else {
      gpsHasFix = false;
    }
  }
}

// แยกข้อมูลจาก $GNGGA / $GPGGA เพื่อหาจำนวนดาวเทียม
void parseGGA(String gga) {
  // ฟอร์แมต: $GNGGA,time,lat,N,lon,E,fix,num_satellites,...
  int index = 0;
  String fields[15];
  int from = 0;
  
  for (int i = 0; i < gga.length() && index < 15; i++) {
    if (gga.charAt(i) == ',' || i == gga.length() - 1) {
      fields[index++] = gga.substring(from, i);
      from = i + 1;
    }
  }
  
  if (index >= 8) {
    gpsSatellites = fields[7].toInt();
  }
}
