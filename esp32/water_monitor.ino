/**
 * ESP32 Smart Water Monitor Firmware
 * ====================================
 * Hardware:
 *   - YF-S201 Flow Sensor   → GPIO 18
 *   - HC-SR04 Ultrasonic    → TRIG GPIO 5, ECHO GPIO 19
 *
 * Communication:
 *   - Wi-Fi + MQTT over TLS (HiveMQ Cloud port 8883)
 *
 * Publishes JSON to topic: water/data
 * {
 *   "flow_rate": 12.5,   // L/min
 *   "tank_level": 65.0   // percent
 * }
 *
 * Libraries required (install via Arduino Library Manager):
 *   - PubSubClient  (Nick O'Leary)
 *   - ArduinoJson   (Benoit Blanchon)
 *   - WiFiClientSecure (built-in ESP32)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ─────────────────────────────────────────────────────────────
//  USER CONFIGURATION  ← fill in your credentials
// ─────────────────────────────────────────────────────────────

// Wi-Fi
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// HiveMQ Cloud
const char* MQTT_BROKER   = "YOUR_CLUSTER.hivemq.cloud";
const int   MQTT_PORT     = 8883;
const char* MQTT_USERNAME = "YOUR_HIVEMQ_USERNAME";
const char* MQTT_PASSWORD = "YOUR_HIVEMQ_PASSWORD";
const char* MQTT_TOPIC    = "water/data";
const char* CLIENT_ID     = "esp32-water-sensor";

// Tank geometry
const float TANK_HEIGHT_CM = 100.0;   // total depth of tank in cm

// Publish interval
const unsigned long PUBLISH_INTERVAL_MS = 3000;   // every 3 seconds

// ─────────────────────────────────────────────────────────────
//  PIN DEFINITIONS
// ─────────────────────────────────────────────────────────────

#define FLOW_SENSOR_PIN   18
#define ULTRASONIC_TRIG   5
#define ULTRASONIC_ECHO   19

// ─────────────────────────────────────────────────────────────
//  GLOBALS
// ─────────────────────────────────────────────────────────────

volatile uint32_t  pulseCount    = 0;
float              flowRate      = 0.0;
unsigned long      lastFlowCalc  = 0;
unsigned long      lastPublish   = 0;

WiFiClientSecure  secureClient;
PubSubClient      mqttClient(secureClient);

// ─────────────────────────────────────────────────────────────
//  ISR — count pulses from YF-S201
// ─────────────────────────────────────────────────────────────

void IRAM_ATTR flowISR() {
  pulseCount++;
}

// ─────────────────────────────────────────────────────────────
//  ULTRASONIC — get distance in cm
// ─────────────────────────────────────────────────────────────

float getDistanceCm() {
  digitalWrite(ULTRASONIC_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(ULTRASONIC_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(ULTRASONIC_TRIG, LOW);

  long duration = pulseIn(ULTRASONIC_ECHO, HIGH, 30000); // 30 ms timeout
  if (duration == 0) return -1.0;   // timeout / out of range
  return (duration * 0.0343f) / 2.0f;
}

float distanceToTankLevel(float distCm) {
  if (distCm < 0) return 0.0;
  // Sensor mounted at the top; closer = fuller
  float waterHeight = TANK_HEIGHT_CM - distCm;
  float level       = (waterHeight / TANK_HEIGHT_CM) * 100.0f;
  return constrain(level, 0.0f, 100.0f);
}

// ─────────────────────────────────────────────────────────────
//  FLOW RATE — calculate L/min
// ─────────────────────────────────────────────────────────────

void calculateFlowRate() {
  unsigned long now     = millis();
  unsigned long elapsed = now - lastFlowCalc;
  if (elapsed < 1000) return;   // calculate once per second

  noInterrupts();
  uint32_t pulses = pulseCount;
  pulseCount      = 0;
  interrupts();

  // YF-S201 calibration: 7.5 pulses per second = 1 L/min
  flowRate    = (pulses / 7.5f) * (1000.0f / elapsed);
  lastFlowCalc = now;
}

// ─────────────────────────────────────────────────────────────
//  Wi-Fi
// ─────────────────────────────────────────────────────────────

void connectWiFi() {
  Serial.print("[WiFi] Connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Connected. IP: " + WiFi.localIP().toString());
}

// ─────────────────────────────────────────────────────────────
//  MQTT
// ─────────────────────────────────────────────────────────────

void connectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Connecting to broker…");
    if (mqttClient.connect(CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD)) {
      Serial.println(" connected!");
    } else {
      Serial.print(" failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" – retrying in 5 s");
      delay(5000);
    }
  }
}

void publishSensorData(float flow, float tankLevel) {
  StaticJsonDocument<128> doc;
  doc["flow_rate"]  = round(flow * 100.0f) / 100.0f;
  doc["tank_level"] = round(tankLevel * 10.0f) / 10.0f;

  char buffer[128];
  serializeJson(doc, buffer);

  bool ok = mqttClient.publish(MQTT_TOPIC, buffer, true);  // retained
  if (ok) {
    Serial.printf("[MQTT] Published → %s\n", buffer);
  } else {
    Serial.println("[MQTT] Publish failed.");
  }
}

// ─────────────────────────────────────────────────────────────
//  SETUP
// ─────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n=== ESP32 Smart Water Monitor ===");

  // Pin modes
  pinMode(FLOW_SENSOR_PIN, INPUT_PULLUP);
  pinMode(ULTRASONIC_TRIG, OUTPUT);
  pinMode(ULTRASONIC_ECHO, INPUT);

  // Attach ISR for flow sensor
  attachInterrupt(digitalPinToInterrupt(FLOW_SENSOR_PIN), flowISR, RISING);

  // Connect Wi-Fi
  connectWiFi();

  // TLS: skip certificate verification for HiveMQ Cloud
  // In production, load the HiveMQ root CA with secureClient.setCACert(…)
  secureClient.setInsecure();

  // MQTT config
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setKeepAlive(60);
  mqttClient.setBufferSize(256);

  connectMQTT();

  lastFlowCalc = millis();
  lastPublish  = millis();
}

// ─────────────────────────────────────────────────────────────
//  LOOP
// ─────────────────────────────────────────────────────────────

void loop() {
  // Maintain connections
  if (WiFi.status() != WL_CONNECTED) connectWiFi();
  if (!mqttClient.connected())       connectMQTT();
  mqttClient.loop();

  // Recalculate flow rate every second
  calculateFlowRate();

  // Publish at the configured interval
  if (millis() - lastPublish >= PUBLISH_INTERVAL_MS) {
    float distCm    = getDistanceCm();
    float tankLevel = distanceToTankLevel(distCm);

    Serial.printf("[Sensor] Flow: %.2f L/min | Tank: %.1f%% (dist %.1f cm)\n",
                  flowRate, tankLevel, distCm);

    publishSensorData(flowRate, tankLevel);
    lastPublish = millis();
  }
}
