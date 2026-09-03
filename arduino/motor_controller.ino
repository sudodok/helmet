// Helmet Detection - Motor Controller
// สำหรับ Arduino/ESP32

#include <ArduinoJson.h>

const int MOTOR_PWM_PIN = 9;
const int BUZZER_PIN = 8;
const int LED_GREEN = 7;
const int LED_RED = 6;

int maxSpeed = 255;  // 0-255 PWM
bool helmetDetected = true;
int currentSpeed = 0;

void setup() {
  Serial.begin(9600);
  pinMode(MOTOR_PWM_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  
  digitalWrite(LED_GREEN, HIGH);
  Serial.println("Motor Controller Ready");
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    processCommand(command);
  }
  
  // จำกัดความเร็วมอเตอร์
  int limitedSpeed = map(
    currentSpeed, 0, 255, 
    0, maxSpeed
  );
  analogWrite(MOTOR_PWM_PIN, limitedSpeed);
  
  // แสดงสถานะ LED
  if (helmetDetected) {
    digitalWrite(LED_GREEN, HIGH);
    digitalWrite(LED_RED, LOW);
  } else {
    digitalWrite(LED_GREEN, LOW);
    digitalWrite(LED_RED, HIGH);
    
    // เสียงเตือนทุก 2 วินาที
    if (millis() % 2000 < 100) {
      tone(BUZZER_PIN, 1000, 100);
    }
  }
  
  delay(10);
}

void processCommand(String cmd) {
  if (cmd.startsWith("SPEED_LIMIT:")) {
    String value = cmd.substring(12);
    
    if (value == "NONE") {
      maxSpeed = 255;
      helmetDetected = true;
      Serial.println("Speed limit removed");
    } else {
      int speedKmh = value.toInt();
      maxSpeed = map(speedKmh, 0, 80, 0, 255);
      helmetDetected = false;
      Serial.print("Speed limited to: ");
      Serial.print(speedKmh);
      Serial.println(" km/h");
    }
  }
}
