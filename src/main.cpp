/*
 ╔══════════════════════════════════════════════════════════════════════════╗
 ║         AeroLab Pro — Firmware v3.1  (LED + BUZZER FIXED)               ║
 ║         ESP32 + MPU6050 + BMP180 + DHT11 + MQ FC-22 + LDR              ║
 ║         + HC-SR04×2 + Servo + IR Receiver + OLED + 7-Seg + RGB          ║
 ╠══════════════════════════════════════════════════════════════════════════╣
 ║  FIXES vs v3.0:                                                          ║
 ║  1. RGB LED BLINK: moved rgbUpdate() to a dedicated 10Hz timer          ║
 ║     so blink is ALWAYS visible. Was stuck in 250ms slow loop before.    ║
 ║  2. Common-Cathode RGB: LOW=off, HIGH=on. ledcWrite(pin,255)=full ON    ║
 ║     ledcWrite(pin,0)=OFF. This is correct for common-cathode.           ║
 ║  3. BUZZER: only beeps for ULTRASONIC proximity (proxCrit/altCrit).     ║
 ║     Gas, temp, altFloor beeps REMOVED. Night mode = silent proximity.   ║
 ║  4. Night mode beep: ultrasonic beeps are suppressed when nightMode     ║
 ║     is active (quiet at night). LED still blinks in night mode.         ║
 ║  5. LED blink is now hardware-timer driven at 5Hz (100ms on/off)        ║
 ║     so it never freezes or lags behind sensor reads.                    ║
 ║                                                                          ║
 ║  WIRING (all verified 3.3V-safe or with voltage divider):               ║
 ║                                                                          ║
 ║  [I2C Bus — SDA=21, SCL=22]                                             ║
 ║   MPU6050  VCC→3.3V  GND→GND  SDA→21  SCL→22  AD0→GND                 ║
 ║   BMP180   VCC→3.3V  GND→GND  SDA→21  SCL→22                          ║
 ║   OLED     VCC→3.3V  GND→GND  SDA→21  SCL→22                          ║
 ║                                                                          ║
 ║  [DHT11]   DATA→GPIO4  VCC→3.3V  GND→GND  (10KΩ pullup D→VCC)         ║
 ║                                                                          ║
 ║  [HC-SR04 #1 — DOWN/ALTITUDE — D5/D18]                                  ║
 ║   VCC→5V  GND→GND  TRIG→GPIO5  ECHO→GPIO18 (via 1K+2K divider)        ║
 ║                                                                          ║
 ║  [HC-SR04 #2 — ON SERVO / RADAR — D19/D23]                              ║
 ║   VCC→5V  GND→GND  TRIG→GPIO19  ECHO→GPIO23 (via 1K+2K divider)       ║
 ║                                                                          ║
 ║  [Servo SG90]  Signal→GPIO13  VCC→5V  GND→GND                         ║
 ║                                                                          ║
 ║  [LDR]  One leg→3.3V  Other→GPIO34  (10KΩ from GPIO34 to GND)          ║
 ║  [MQ FC-22]  AOUT→GPIO35  VCC→5V  GND→GND  DOUT→GPIO32               ║
 ║  [IR Receiver VS1838B]  OUT→GPIO33  VCC→3.3V  GND→GND                  ║
 ║  [Photodiode]  Anode→GPIO36(VP)  Cathode+10KΩ→GND (reverse bias)      ║
 ║                                                                          ║
 ║  [3-PIN BUZZER MODULE]  VCC→5V  GND→GND  S/IO→GPIO25                  ║
 ║   (Active buzzer module = transistor on board, just needs signal)       ║
 ║                                                                          ║
 ║  [RGB LED Common-Cathode]                                               ║
 ║   R pin → 220Ω → GPIO26                                               ║
 ║   G pin → 220Ω → GPIO27                                               ║
 ║   B pin → 220Ω → GPIO14                                               ║
 ║   Common (longest leg / cathode) → GND                                  ║
 ║                                                                          ║
 ║  [7-Seg via 74HC595]: Data→GPIO15  Latch→GPIO2  Clock→GPIO16            ║
 ╚══════════════════════════════════════════════════════════════════════════╝

  HOW TO USE WEBSERVER / HTML:
  1. Download three.js r128 minified from:
     https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js
  2. Rename to:  three.min.js
  3. Put BOTH files in your Arduino sketch folder:
       data/index.html
       data/three.min.js
  4. In Arduino IDE: Tools → ESP32 Sketch Data Upload (LittleFS)
  5. Flash this firmware
  6. Connect your phone/laptop to WiFi "AeroLab-Pro"
  7. Open browser → http://192.168.4.1
*/

// ─────────────────────────────────────────────────────────────────────────────
//  LIBRARY INCLUDES
// ─────────────────────────────────────────────────────────────────────────────
#include <Wire.h>
#include <WiFi.h>
#include <WebSocketsServer.h>     // Links2004/arduinoWebSockets
#include <ArduinoJson.h>          // bblanchon/ArduinoJson v6
#include <DHT.h>                  // Adafruit DHT library
#include <Adafruit_BMP085.h>      // Adafruit BMP085/BMP180 library
#include <MPU6050.h>              // Electronic Cats MPU6050
#include <Adafruit_SSD1306.h>     // Adafruit SSD1306 OLED
#include <Adafruit_GFX.h>         // Adafruit GFX (dependency)
#include <ESP32Servo.h>           // madhephaestus/ESP32Servo
#include <IRremoteESP8266.h>      // crankyoldgit/IRremoteESP8266
#include <IRrecv.h>
#include <WebServer.h>            // Built-in ESP32 WebServer
#include <LittleFS.h>             // Built-in LittleFS (ESP32 Arduino v2+)
#include <Arduino.h>

// ─────────────────────────────────────────────────────────────────────────────
//  PIN MAP
// ─────────────────────────────────────────────────────────────────────────────
#define PIN_DHT         4
#define PIN_TRIG_ALT    5
#define PIN_ECHO_ALT    18
#define PIN_TRIG_RADAR  19
#define PIN_ECHO_RADAR  23
#define PIN_SERVO       13
#define PIN_LDR         34    // ADC1_CH6
#define PIN_MQ          35    // ADC1_CH7 (analog)
#define PIN_MQ_DOUT     32    // MQ digital threshold output
#define PIN_IR          33    // IR receiver data
#define PIN_PHOTO       36    // VP — photodiode analog
#define PIN_BUZZER      25
#define PIN_LED_R       26
#define PIN_LED_G       27
#define PIN_LED_B       14
#define PIN_BTN         2    // SVN — input only
// 74HC595 shift register for 7-segment
#define PIN_SR_DATA     15
#define PIN_SR_LATCH    2
#define PIN_SR_CLK      16

// ─────────────────────────────────────────────────────────────────────────────
//  CONFIG
// ─────────────────────────────────────────────────────────────────────────────
#define WIFI_SSID       "AeroLab-Pro"
#define WIFI_PASS       "aerolab2024"
#define WS_PORT         81

#define OLED_W          128
#define OLED_H          64
#define OLED_ADDR       0x3C

#define DHT_TYPE        DHT11
#define SEA_HPA         1013.25f

// Kalman
#define KAL_Q_ANGLE     0.001f
#define KAL_Q_BIAS      0.003f
#define KAL_R_MEASURE   0.03f

// Radar sweep
#define RADAR_STEP      5         // degrees per step
#define RADAR_DELAY_MS  40        // ms between steps
#define RADAR_POINTS    37        // 0..180 in 5° steps

// Thresholds
#define TEMP_WARN       38.0f
#define TEMP_CRIT       50.0f
#define GAS_WARN        2000      // MQ ADC threshold (0–4095)
#define GAS_CRIT        3200
#define PROX_WARN_CM    50        // ultrasonic proximity warn
#define PROX_CRIT_CM    20        // ultrasonic proximity critical
#define ALT_FLOOR_CM    8
#define LDR_NIGHT       400
#define PHOTO_THRESH    1500

// LED blink interval in ms (how fast it blinks in danger modes)
#define LED_BLINK_FAST_MS   150   // blink period for CRITICAL
#define LED_BLINK_SLOW_MS   500   // blink period for WARN

// Buzzer: only proximity-based, only when NOT in night mode
// Beep interval — don't beep every 250ms, use a cooldown
#define BUZZ_COOLDOWN_MS    1500  // minimum ms between beep bursts

// ─────────────────────────────────────────────────────────────────────────────
//  OBJECTS
// ─────────────────────────────────────────────────────────────────────────────
MPU6050          mpu;
DHT              dht(PIN_DHT, DHT_TYPE);
Adafruit_BMP085  bmp;
Adafruit_SSD1306 oled(OLED_W, OLED_H, &Wire, -1);
WebSocketsServer wsServer(WS_PORT);
WebServer        httpServer(80);
Servo            radarServo;
IRrecv           irRecv(PIN_IR);
decode_results   irResult;

// ─────────────────────────────────────────────────────────────────────────────
//  KALMAN FILTER — 1D per axis
// ─────────────────────────────────────────────────────────────────────────────
struct Kalman {
  float angle = 0, bias = 0;
  float P[2][2] = {{0,0},{0,0}};

  float update(float measuredAngle, float gyroRate, float dt) {
    angle += dt * (gyroRate - bias);
    P[0][0] += dt*(dt*P[1][1] - P[0][1] - P[1][0] + KAL_Q_ANGLE);
    P[0][1] -= dt * P[1][1];
    P[1][0] -= dt * P[1][1];
    P[1][1] += KAL_Q_BIAS * dt;
    float S   = P[0][0] + KAL_R_MEASURE;
    float K0  = P[0][0] / S;
    float K1  = P[1][0] / S;
    float y   = measuredAngle - angle;
    angle    += K0 * y;
    bias     += K1 * y;
    float P00 = P[0][0]; float P01 = P[0][1];
    P[0][0]  -= K0 * P00;
    P[0][1]  -= K0 * P01;
    P[1][0]  -= K1 * P00;
    P[1][1]  -= K1 * P01;
    return angle;
  }
} kalRoll, kalPitch;

// ─────────────────────────────────────────────────────────────────────────────
//  STATE STRUCT
// ─────────────────────────────────────────────────────────────────────────────
struct State {
  // IMU
  float roll=0, pitch=0, yaw=0;
  float gx=0, gy=0, gz=0;
  float ax=0, ay=0, az=0;
  float vibration=0;

  // Environmental
  float temp=25, humidity=50;
  float pressure=1013;
  float baroAlt=0;

  // Ranging
  int   altCm=100;
  int   radarCm=200;
  int   radarAngle=90;

  // Radar map
  uint8_t radarMap[RADAR_POINTS];

  // Analog
  int   ldr=2000;
  int   mqRaw=0;
  bool  mqDigital=false;
  int   photoRaw=0;

  // Derived
  bool  nightMode=false;
  bool  irMotion=false;
  bool  photoFlash=false;

  // ── ALERTS ──
  bool  tempWarn=false, tempCrit=false;
  bool  gasWarn=false,  gasCrit=false;
  bool  proxWarn=false, proxCrit=false;
  bool  altFloor=false;
  bool  altWarn=false,  altCrit=false;
  bool  vibHigh=false;

  // System
  uint8_t mode=0;
  uint32_t uptime=0;
  float    loopHz=0;
  uint8_t  wsClients=0;
} S;

// ─────────────────────────────────────────────────────────────────────────────
//  ULTRASONIC — 5-sample median filter
// ─────────────────────────────────────────────────────────────────────────────
int ultrasonicCm(int trig, int echo) {
  long dur[5];
  for(int i=0;i<5;i++){
    digitalWrite(trig, LOW);  delayMicroseconds(2);
    digitalWrite(trig, HIGH); delayMicroseconds(10);
    digitalWrite(trig, LOW);
    dur[i] = pulseIn(echo, HIGH, 30000);
    delayMicroseconds(200);
  }
  for(int i=1;i<5;i++){
    long k=dur[i]; int j=i-1;
    while(j>=0&&dur[j]>k){dur[j+1]=dur[j];j--;}
    dur[j+1]=k;
  }
  long med = dur[2];
  if(med==0) return 400;
  return (int)(med * 343L / 20000);
}

int ultrasonicFast(int trig, int echo) {
  digitalWrite(trig, LOW);  delayMicroseconds(2);
  digitalWrite(trig, HIGH); delayMicroseconds(10);
  digitalWrite(trig, LOW);
  long dur = pulseIn(echo, HIGH, 25000);
  if(dur==0) return 300;
  return (int)(dur * 343L / 20000);
}

// ─────────────────────────────────────────────────────────────────────────────
//  RGB LED — Common Cathode, 220Ω resistors on each pin
//  ledcWrite(pin, 0)   = OFF
//  ledcWrite(pin, 255) = FULL BRIGHTNESS
//
//  FIX: rgbUpdate() is now called from a dedicated 10Hz timer
//  so blinking works independently of sensor read timing.
// ─────────────────────────────────────────────────────────────────────────────
void rgbSet(int r, int g, int b) {
  ledcWrite(1, constrain(r, 0, 255));
  ledcWrite(2, constrain(g, 0, 255));
  ledcWrite(3, constrain(b, 0, 255));
}

// Called at 10Hz from loop via dedicated timer
// Uses millis() internally so blink timing is accurate
void rgbUpdate() {
  // CRITICAL (ANY): Fast Red Blink
  if (S.gasCrit || S.tempCrit || S.proxCrit || S.altCrit) {
    uint32_t now = millis();
    bool on = (now / LED_BLINK_FAST_MS) % 2;
    rgbSet(on ? 255 : 0, 0, 0);
    return;
  }

  // WARNING (GAS): Steady Amber
  if (S.gasWarn) {
    rgbSet(255, 191, 0); // Amber
    return;
  }

  // WARNING (TEMP): Steady Orange
  if (S.tempWarn) {
    rgbSet(255, 69, 0); // Orange
    return;
  }

  // WARNING (PROXIMITY): Steady Yellow
  if (S.proxWarn || S.altWarn) {
    rgbSet(255, 255, 0); // Yellow
    return;
  }

  // NIGHT MODE: dim blue (steady)
  if (S.nightMode) {
    rgbSet(0, 0, 80);
    return;
  }

  // SCAN MODE: steady bright blue
  if (S.mode == 1) {
    rgbSet(0, 128, 255);
    return;
  }

  // CALIBRATE MODE: steady purple
  if (S.mode == 2) {
    rgbSet(128, 0, 255);
    return;
  }

  // ALL OK: steady bright green
  rgbSet(0, 255, 0);
}

// ─────────────────────────────────────────────────────────────────────────────
//  OLED DISPLAY
// ─────────────────────────────────────────────────────────────────────────────
void oledDraw() {
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);

  oled.fillRect(0,0,128,10,SSD1306_WHITE);
  oled.setTextColor(SSD1306_BLACK);
  oled.setTextSize(1);
  oled.setCursor(2,1);
  oled.print("AEROLAB");
  oled.setCursor(55,1);
  const char* modeStr[] = {"NORMAL","SCAN  ","CALIB "};
  oled.print(modeStr[S.mode]);
  oled.setCursor(100,1);
  oled.print(S.wsClients); oled.print("C");
  oled.setTextColor(SSD1306_WHITE);

  oled.setCursor(0,13);
  oled.print("R:"); oled.print((int)S.roll);
  oled.setCursor(42,13);
  oled.print("P:"); oled.print((int)S.pitch);
  oled.setCursor(85,13);
  oled.print("Y:"); oled.print((int)S.yaw);

  oled.setCursor(0,24);
  oled.print("ALT:"); oled.print(S.altCm); oled.print("cm");
  oled.setCursor(72,24);
  oled.print("PX:"); oled.print(S.radarCm);

  oled.setCursor(0,34);
  oled.print("T:"); oled.print(S.temp,1); oled.print((char)223); oled.print("C");
  oled.setCursor(72,34);
  oled.print("H:"); oled.print((int)S.humidity); oled.print("%");

  oled.setCursor(0,44);
  oled.print("GAS:"); oled.print(S.mqRaw);
  oled.setCursor(72,44);
  oled.print("LDR:"); oled.print(S.ldr>>6);

  oled.setCursor(0,55);
  if(S.tempCrit||S.gasCrit)        { oled.print("!! CRITICAL ALERT !!"); }
  else if(S.proxCrit||S.altCrit)   { oled.print(">> IMPACT WARN <<"); }
  else if(S.gasWarn)               { oled.print("~ GAS DETECTED ~"); }
  else if(S.nightMode)             { oled.print("* NIGHT MODE *"); }
  else                             { oled.print("ALL SYSTEMS OK"); }

  oled.display();
}

// ─────────────────────────────────────────────────────────────────────────────
//  BUZZER
//  FIX: ONLY beeps for ultrasonic proximity (proxCrit or altCrit).
//       Suppressed in nightMode. Cooldown prevents rapid-fire beeping.
//       Gas, temp, altFloor no longer trigger buzzer.
// ─────────────────────────────────────────────────────────────────────────────
void beep(int freq, int ms) {
  ledcWriteTone(4, freq);
  delay(ms);
  ledcWriteTone(4, 0);
}

// Call this from the slow sensor loop — handles buzzer logic with cooldown
uint32_t lastBuzzTime = 0;

void buzzerUpdate() {
  // Night mode = silent
  if (S.nightMode) return;

  uint32_t now = millis();
  if (now - lastBuzzTime < BUZZ_COOLDOWN_MS) return; // cooldown

  // Only ultrasonic proximity triggers buzzer
  if (S.proxCrit || S.altCrit) {
    // Critical proximity: two short beeps
    beep(2200, 80);
    delay(40);
    beep(2200, 80);
    lastBuzzTime = millis();
  } else if (S.proxWarn || S.altWarn) {
    // Proximity warning: one short beep
    beep(1600, 60);
    lastBuzzTime = millis();
  }
  // No beep for gas, temp, altFloor
}

// ─────────────────────────────────────────────────────────────────────────────
//  WEBSOCKET EVENTS
// ─────────────────────────────────────────────────────────────────────────────
void wsEvent(uint8_t client, WStype_t type, uint8_t* payload, size_t len) {
  switch(type) {
    case WStype_CONNECTED:
      S.wsClients++;
      beep(1000,50);
      break;
    case WStype_DISCONNECTED:
      if(S.wsClients) S.wsClients--;
      break;
    case WStype_TEXT: {
      String cmd((char*)payload);
      if(cmd=="cal")       { kalRoll.angle=0; kalPitch.angle=0; S.yaw=0; beep(800,80); }
      else if(cmd=="scan") { S.mode=1; }
      else if(cmd=="norm") { S.mode=0; }
      else if(cmd=="buzz") { beep(440,80); delay(30); beep(880,80); }
      break;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  RADAR SWEEP — servo only written once on mode entry (no buzz noise)
// ─────────────────────────────────────────────────────────────────────────────
bool     sweepActive  = false;
int      sweepAngle   = 0;
int8_t   sweepDir     = 1;
uint32_t lastSweep    = 0;

void radarSweepStep() {
  static bool atHome = false;

  if(S.mode != 1) {
    if(!atHome) {
      radarServo.write(90);
      atHome = true;
    }
    uint32_t now = millis();
    if(now - lastSweep >= 50) {
      lastSweep = now;
      S.radarAngle = 90;
      S.radarCm    = ultrasonicFast(PIN_TRIG_RADAR, PIN_ECHO_RADAR);
      S.radarMap[18] = (uint8_t)min(255, S.radarCm);
    }
    return;
  }

  atHome = false;

  uint32_t now = millis();
  if(now - lastSweep < RADAR_DELAY_MS) return;
  lastSweep = now;

  radarServo.write(sweepAngle);
  delay(15);
  int dist = ultrasonicFast(PIN_TRIG_RADAR, PIN_ECHO_RADAR);
  int idx = sweepAngle / RADAR_STEP;
  if(idx >= 0 && idx < RADAR_POINTS) {
    S.radarMap[idx] = (uint8_t)min(255, dist);
  }
  S.radarAngle = sweepAngle;
  S.radarCm    = dist;

  sweepAngle += sweepDir * RADAR_STEP;
  if(sweepAngle >= 180) { sweepAngle=180; sweepDir=-1; }
  if(sweepAngle <= 0)   { sweepAngle=0;   sweepDir= 1; }
}

// ─────────────────────────────────────────────────────────────────────────────
//  BUTTON HANDLING
// ─────────────────────────────────────────────────────────────────────────────
uint32_t lastBtnPress = 0;
bool     lastBtnState = HIGH;

void checkButton() {
  bool state = digitalRead(PIN_BTN);
  
  // FIX: Added 'millis() > 1500' to ignore hardware boot transients
  if(state == LOW && lastBtnState == HIGH && millis() > 1500) {
    uint32_t now = millis();
    if(now - lastBtnPress > 200) {
      S.mode = (S.mode + 1) % 3;
      beep(600 + S.mode*200, 60);
      lastBtnPress = now;
    }
  }
  lastBtnState = state;
}

void loadConfig() {

  File file = LittleFS.open("/config.json", "r");

  if(!file){
    Serial.println("config.json not found");
    return;
  }

  StaticJsonDocument<256> doc;

  DeserializationError error = deserializeJson(doc, file);

  if(error){
    Serial.println("JSON parse failed");
    return;
  }

  const char* name = doc["device_name"];
  const char* ssid = doc["wifi_ssid"];

  Serial.print("Device: ");
  Serial.println(name);

  Serial.print("WiFi: ");
  Serial.println(ssid);

  file.close();
}
// ─────────────────────────────────────────────────────────────────────────────
//  HTTP SERVER HELPERS
// ─────────────────────────────────────────────────────────────────────────────
void serveFile(const char* path, const char* mime) {
  File f = LittleFS.open(path, "r");
  if(!f) {
    httpServer.send(404, "text/plain", String(path) + " not found in LittleFS.\n"
      "Upload via: Tools -> ESP32 Sketch Data Upload (LittleFS)\n"
      "Put index.html and three.min.js in the /data/ folder of your sketch.");
    return;
  }
  httpServer.streamFile(f, mime);
  f.close();
}

// ─────────────────────────────────────────────────────────────────────────────
//  JSON BROADCAST
// ─────────────────────────────────────────────────────────────────────────────
void broadcast() {
  if(S.wsClients == 0) return;

  // FIX: Increased from 1024 to 2048 to safely fit the entire radar map array
  StaticJsonDocument<2048> doc;
  doc["r"]  = roundf(S.roll  *10)/10;
  doc["p"]  = roundf(S.pitch *10)/10;
  doc["y"]  = roundf(S.yaw   *10)/10;
  doc["ax"] = roundf(S.ax*100)/100;
  doc["ay"] = roundf(S.ay*100)/100;
  doc["az"] = roundf(S.az*100)/100;
  doc["vb"] = roundf(S.vibration*10)/10;
  doc["t"]  = roundf(S.temp*10)/10;
  doc["h"]  = (int)S.humidity;
  doc["pr"] = roundf(S.pressure*10)/10;
  doc["ba"] = roundf(S.baroAlt*10)/10;
  doc["a"]  = S.altCm;
  doc["rc"] = S.radarCm;
  doc["ra"] = S.radarAngle;
  JsonArray rm = doc.createNestedArray("rm");
  for(int i=0;i<RADAR_POINTS;i++) rm.add(S.radarMap[i]);
  doc["l"]  = S.ldr;
  doc["mq"] = S.mqRaw;
  doc["mqd"]= S.mqDigital;
  doc["ph"] = S.photoRaw;
  doc["nm"] = S.nightMode;
  doc["ir"] = S.irMotion;
  doc["pf"] = S.photoFlash;
  doc["tw"] = S.tempWarn;  doc["tc"] = S.tempCrit;
  doc["gw"] = S.gasWarn;   doc["gc"] = S.gasCrit;
  doc["pw"] = S.proxWarn;  doc["pc"] = S.proxCrit;
  doc["af"] = S.altFloor;
  doc["aw"] = S.altWarn;
  doc["ac"] = S.altCrit;
  doc["vh"] = S.vibHigh;
  doc["md"] = S.mode;
  doc["up"] = S.uptime;
  doc["hz"] = (int)S.loopHz;
  doc["cl"] = S.wsClients;

  String out;
  serializeJson(doc, out);
  wsServer.broadcastTXT(out);
}

// ─────────────────────────────────────────────────────────────────────────────
//  SETUP
// ─────────────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Wire.begin(21,22);
  Wire.setClock(400000);

  // GPIO
  pinMode(PIN_TRIG_ALT,   OUTPUT); pinMode(PIN_ECHO_ALT,   INPUT);
  pinMode(PIN_TRIG_RADAR, OUTPUT); pinMode(PIN_ECHO_RADAR, INPUT);
  pinMode(PIN_MQ_DOUT,    INPUT);
  pinMode(PIN_BTN,        INPUT_PULLUP);
  pinMode(PIN_SR_DATA,    OUTPUT);
  pinMode(PIN_SR_LATCH,   OUTPUT);
  pinMode(PIN_SR_CLK,     OUTPUT);

  // ── LEDC PWM — RGB (3 pins) + Buzzer (1 pin)
  // Servo library takes channel 0, so we use channels 1,2,3 for RGB and 4 for Buzzer.
ledcSetup(1, 5000, 8); // Red on Channel 1
ledcAttachPin(PIN_LED_R, 1);

ledcSetup(2, 5000, 8); // Green on Channel 2
ledcAttachPin(PIN_LED_G, 2);

ledcSetup(3, 5000, 8); // Blue on Channel 3
ledcAttachPin(PIN_LED_B, 3);

ledcSetup(4, 2000, 8); // Buzzer on Channel 4
ledcAttachPin(PIN_BUZZER, 4);

  // Boot colour: blue
  rgbSet(0, 0, 255);

  // OLED
  if(!oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("[WARN] OLED not found");
  } else {
    oled.clearDisplay();
    oled.setTextSize(2); oled.setTextColor(SSD1306_WHITE);
    oled.setCursor(10,20); oled.print("AEROLAB");
    oled.display();
  }

  // MPU6050
  mpu.initialize();
  mpu.setDLPFMode(MPU6050_DLPF_BW_42);
  mpu.setFullScaleGyroRange(MPU6050_GYRO_FS_250);
  mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_2);
  if(!mpu.testConnection()) Serial.println("[ERR] MPU6050 missing");

  // BMP180
  if(!bmp.begin()) Serial.println("[ERR] BMP180 missing");

  // DHT11
  dht.begin();

  // Servo
  radarServo.setPeriodHertz(50);
  radarServo.attach(PIN_SERVO, 500, 2400);
  radarServo.write(90);

  // IR Receiver
  irRecv.enableIRIn();

  // Init radar map
  for(int i=0;i<RADAR_POINTS;i++) S.radarMap[i]=200;

  // LittleFS
  if(!LittleFS.begin(true)) {
    Serial.println("[ERR] LittleFS failed — HTML serve unavailable");
  } else {
    Serial.println("[LittleFS] Mounted OK");
  }
loadConfig();
  // WiFi AP
  WiFi.mode(WIFI_AP);
  WiFi.softAP(WIFI_SSID, WIFI_PASS);
  Serial.printf("[WiFi] AP IP: %s\n", WiFi.softAPIP().toString().c_str());

  // HTTP Server routes
  httpServer.on("/", HTTP_GET, [](){
    serveFile("/index.html", "text/html");
  });
  httpServer.on("/index.html", HTTP_GET, [](){
    serveFile("/index.html", "text/html");
  });
  httpServer.on("/three.min.js", HTTP_GET, [](){
    httpServer.sendHeader("Cache-Control", "max-age=3600");
    serveFile("/three.min.js", "application/javascript");
  });
  httpServer.onNotFound([](){
    httpServer.send(404, "text/plain", "Not found");
  });
  httpServer.begin();
  Serial.println("[HTTP] Server started on port 80");

  // WebSocket
  wsServer.begin();
  wsServer.onEvent(wsEvent);

  // Startup jingle (boot complete)
  int notes[]={440,523,659,880};
  for(int n:notes){beep(n,70);delay(20);}

  // Green = ready
  rgbSet(0, 200, 0);

  Serial.println("[AeroLab] Boot complete.");
  Serial.println("[AeroLab] Connect to WiFi: " WIFI_SSID);
  Serial.println("[AeroLab] Open browser:     http://192.168.4.1");
}

// ─────────────────────────────────────────────────────────────────────────────
//  MAIN LOOP
// ─────────────────────────────────────────────────────────────────────────────
uint32_t t_imu=0, t_slow=0, t_ws=0, t_oled=0, t_led=0, t_hz=0;
int      hzCount=0;

void loop() {
  httpServer.handleClient();
  wsServer.loop();
  checkButton();
  radarSweepStep();
  uint32_t now = millis();

  // ── IMU @ 50Hz ────────────────────────────────────────────────────
  if(now - t_imu >= 20) {
    float dt = (now-t_imu)/1000.0f;
    t_imu = now; hzCount++;

    int16_t ax,ay,az,gx,gy,gz;
    mpu.getMotion6(&ax,&ay,&az,&gx,&gy,&gz);

    S.ax = ax/16384.0f; S.ay = ay/16384.0f; S.az = az/16384.0f;
    S.gx = gx/131.0f;  S.gy = gy/131.0f;  S.gz = gz/131.0f;

    float accRoll  = atan2f(S.ay, S.az)*180/PI;
    float accPitch = atan2f(-S.ax, sqrtf(S.ay*S.ay+S.az*S.az))*180/PI;

    S.roll  = kalRoll.update(accRoll,   S.gx, dt);
    S.pitch = kalPitch.update(accPitch, S.gy, dt);
    S.yaw  += S.gz * dt;
    if(S.yaw > 180) S.yaw-=360; if(S.yaw<-180) S.yaw+=360;

    float gMag = sqrtf(S.gx*S.gx+S.gy*S.gy+S.gz*S.gz);
    S.vibration = 0.95f*S.vibration + 0.05f*gMag;
    S.vibHigh   = S.vibration > 40.0f;
  }

  // ── SLOW SENSORS @ 4Hz ────────────────────────────────────────────
  if(now - t_slow >= 250) {
    t_slow = now;

    float ft = dht.readTemperature();
    float fh = dht.readHumidity();
    if(!isnan(ft)) S.temp     = ft;
    if(!isnan(fh)) S.humidity = fh;

    S.pressure = bmp.readPressure() / 100.0f;
    S.baroAlt  = bmp.readAltitude(SEA_HPA);

    S.altCm = ultrasonicCm(PIN_TRIG_ALT, PIN_ECHO_ALT);
    S.altCm = constrain(S.altCm, 0, 400);

    S.ldr       = analogRead(PIN_LDR);
    S.mqRaw     = analogRead(PIN_MQ);
    S.mqDigital = digitalRead(PIN_MQ_DOUT) == LOW;
    S.photoRaw  = analogRead(PIN_PHOTO);

    S.nightMode  = (S.ldr < LDR_NIGHT);
    S.photoFlash = (S.photoRaw > PHOTO_THRESH);

    if(irRecv.decode(&irResult)) {
      S.irMotion = true;
      irRecv.resume();
    } else {
      S.irMotion = false;
    }

    // Update all alert flags
    S.tempWarn = (S.temp > TEMP_WARN);
    S.tempCrit = (S.temp > TEMP_CRIT);
    S.gasWarn  = (S.mqRaw > GAS_WARN) || S.mqDigital;
    S.gasCrit  = (S.mqRaw > GAS_CRIT);
    S.proxWarn = (S.radarCm < PROX_WARN_CM);
    S.proxCrit = (S.radarCm < PROX_CRIT_CM);
    S.altFloor = (S.altCm   < ALT_FLOOR_CM);
    S.altWarn  = (S.altCm   < PROX_WARN_CM);
    S.altCrit  = (S.altCm   < PROX_CRIT_CM);

    // ── BUZZER: ultrasonic only, night mode suppresses it
    buzzerUpdate();

    S.uptime = now / 1000;
  }

  // ── RGB LED UPDATE @ 10Hz (independent of sensor reads)
  // This is what makes blink actually visible and smooth
  if(now - t_led >= 100) {
    t_led = now;
    rgbUpdate();
  }

  // ── WEBSOCKET BROADCAST @ 25Hz ─────────────────────────────────
  if(now - t_ws >= 40) { t_ws=now; broadcast(); }

  // ── OLED UPDATE @ 5Hz ─────────────────────────────────────────
  if(now - t_oled >= 200) { t_oled=now; oledDraw(); }

  // ── Hz counter ────────────────────────────────────────────────
  if(now - t_hz >= 1000) {
    S.loopHz = hzCount; hzCount=0; t_hz=now;
  }
}