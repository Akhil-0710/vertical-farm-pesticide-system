  #include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

//wifi creds
const char* ssid = "Ak";
const char* password = "123456789";

//flask server address
const char* server_url = "http://10.39.32.231:5000/api/analysis/image";
int severity = 0;  // global variable


//cam setup
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27

#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22


//motor and pump setups
#define IN1 13
#define IN2 12
#define PUMP_PIN 14

void motorUp() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
}

void motorDown() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
}

void motorStop() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
}

void initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;  // 640x480, safe size
  config.jpeg_quality = 12;           // lower is better quality
  config.fb_count = 1;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera init failed!");
    while (true)
      ;
  }
}

void setup() {

   pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  // Relay pin
  pinMode(PUMP_PIN, OUTPUT);

  // Start OFF
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(PUMP_PIN, HIGH);  // Active LOW relay (off)


  Serial.begin(115200);
  WiFi.begin(ssid, password);
  Serial.println("Connecting to WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.println(WiFi.localIP());

  initCamera();
}

void sendPhoto() {
  // 1. Capture frame
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed!");
    return;  // don’t dereference NULL fb
  }

  // 2. Prepare HTTP client
  WiFiClient client;
  HTTPClient http;
  if (!http.begin(client, server_url)) {
    Serial.println("HTTP begin failed!");
    esp_camera_fb_return(fb);
    return;
  }
  http.addHeader("Content-Type", "image/jpeg");

  // 3. Upload photo
  int httpResponseCode = http.POST(fb->buf, fb->len);
  esp_camera_fb_return(fb);  // return buffer ASAP to free PSRAM

  if (httpResponseCode <= 0) {
    Serial.printf("Upload failed, error: %s\n",
                  http.errorToString(httpResponseCode).c_str());
    http.end();
    return;
  }

  Serial.printf("Image uploaded, server response: %d\n", httpResponseCode);

  // 4. Read server response safely
  String response = http.getString();
  http.end();

  if (response.length() == 0) {
    Serial.println("Empty server response!");
    return;
  }

  Serial.println("Raw server response:");
  Serial.println(response);

  // 5. Parse JSON safely
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, response);

  if (error) {
    Serial.print("JSON parse failed: ");
    Serial.println(error.c_str());
    severity = -1;
    return;
  }

  // 6. Access infected_percentage field
  if (doc.containsKey("infected_percentage")) {
    severity = doc["infected_percentage"].as<int>();  // round down to int
    Serial.printf("Infection Severity: %d%%\n", severity);
  } else {
    severity = -1;
    Serial.println("Key 'infected_percentage' missing!");
  }
}

int getSprayDurationMs(int severity) {
  if (severity < 0) return 0;       // invalid / error -> no spray
  if (severity <= 24) return 500;     // 0-24% -> no spray
  if (severity <= 49) return 1000;  // 25-49% -> 1s
  if (severity <= 74) return 1100;  // 50-74% -> 2s
  return 1200;                      // 75-100% -> 3s
}

void sprayForDuration(int ms) {
  if (ms == 0) {
    Serial.println("[SPRAY] Decision: NO spray.");
    return;
  }
  Serial.printf("[SPRAY] Turning pump ON for %lu ms\n", ms);
  digitalWrite(PUMP_PIN, LOW);
  delay(ms);
  digitalWrite(PUMP_PIN, HIGH);
  Serial.println("[SPRAY] Pump OFF");
}

void loop() {

  Serial.println("\n===== NEW CYCLE START =====");

  // --- Level 0 (plant 1) ---
  Serial.println("[LEVEL 0] Capturing plant 1 (level 0)...");
  sendPhoto();
  sprayForDuration(getSprayDurationMs(severity));
  delay(4000);  // short rest

  // --- Move UP to Level 1 ---
  Serial.println("[MOVE] Going UP to Level 1");
  motorUp();
  delay(2000);
  motorStop();
  delay(2000);

  // --- Level 1 (plant 2) ---
  Serial.println("[LEVEL 1] Capturing plant 2 (level 1)...");
  sendPhoto();
  sprayForDuration(getSprayDurationMs(severity));
  delay(3000);


  // --- Return DOWN to Level 0 (reset) ---
  Serial.println("[RETURN] Returning DOWN to Level 0 (reset)");
  motorDown();
  delay(2000);
  motorStop();

  Serial.println("[CYCLE] Complete. Pausing before next cycle...");
  delay(4000);
}