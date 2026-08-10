#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <TFT_eSPI.h>
#include <XPT2046_Touchscreen.h>
#include <SPI.h>

// ---- EDIT THESE ----
const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";
const char* RECORDER_IP = "192.168.1.100";   // Shown by desktop app
const uint16_t RECORDER_PORT = 8765;
const char* RECORDER_TOKEN = "000000";  // Copy the 6-digit PIN shown in the desktop SYSTEM card
// --------------------

// Common ESP32-2432S028R (2.8 inch CYD) touch pins.
// Verify against your board revision before compiling.
#define XPT2046_IRQ 36
#define XPT2046_MOSI 32
#define XPT2046_MISO 39
#define XPT2046_CLK 25
#define XPT2046_CS 33

#define TFT_BL 21

SPIClass touchSPI(VSPI);
XPT2046_Touchscreen ts(XPT2046_CS, XPT2046_IRQ);
TFT_eSPI tft = TFT_eSPI();

struct RecorderState {
  bool online = false;
  bool recording = false;
  bool circle = false;
  float elapsed = 0;
  int take = 1;
  int xruns = 0;
  int droppedBlocks = 0;
  float meters[4] = {-80, -80, -80, -80};
  String scene = "1";
  String roll = "A001";
  String lastFile = "";
};

RecorderState state;
unsigned long lastPoll = 0;
unsigned long lastDraw = 0;

struct Button {
  int x, y, w, h;
  const char* label;
  const char* command;
};

Button buttons[] = {
  {10, 118, 95, 56, "REC", "record"},
  {112, 118, 95, 56, "STOP", "stop"},
  {214, 118, 95, 56, "PLAY", "play"},
  {10, 181, 145, 50, "NEXT TAKE", "next_take"},
  {163, 181, 146, 50, "CIRCLE", "circle"}
};
const int BUTTON_COUNT = sizeof(buttons) / sizeof(buttons[0]);

String baseUrl() {
  return String("http://") + RECORDER_IP + ":" + RECORDER_PORT;
}

void sendCommand(const char* command) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(baseUrl() + "/command");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-FilmRec-Token", RECORDER_TOKEN);
  String payload = String("{\"command\":\"") + command + "\",\"request_id\":\"" + String(millis()) + "\"}";
  http.POST(payload);
  http.end();
  delay(60);
  pollStatus();
}

void pollStatus() {
  if (WiFi.status() != WL_CONNECTED) {
    state.online = false;
    return;
  }

  HTTPClient http;
  http.setTimeout(450);
  http.begin(baseUrl() + "/status");
  http.addHeader("X-FilmRec-Token", RECORDER_TOKEN);
  int code = http.GET();
  if (code == 200) {
    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, http.getString());
    if (!err) {
      state.online = true;
      state.recording = doc["recording"] | false;
      state.elapsed = doc["elapsed"] | 0.0;
      state.roll = String((const char*)(doc["roll"] | ""));
      state.scene = String((const char*)(doc["scene"] | ""));
      state.take = doc["take"] | 1;
      state.circle = doc["circle"] | false;
      state.xruns = doc["xruns"] | 0;
      state.droppedBlocks = doc["dropped_blocks"] | 0;
      JsonArray meterArray = doc["meters"].as<JsonArray>();
      for (int i = 0; i < 4; i++) {
        state.meters[i] = (i < meterArray.size()) ? (meterArray[i] | -80.0f) : -80.0f;
      }
      state.lastFile = String((const char*)(doc["last_file"] | ""));
    } else {
      state.online = false;
    }
  } else {
    state.online = false;
  }
  http.end();
}

String elapsedText(float seconds) {
  unsigned long totalMs = (unsigned long)(seconds * 1000.0f);
  int h = totalMs / 3600000UL;
  int m = (totalMs / 60000UL) % 60;
  int s = (totalMs / 1000UL) % 60;
  char buf[16];
  snprintf(buf, sizeof(buf), "%02d:%02d:%02d", h, m, s);
  return String(buf);
}

void drawButton(const Button& b, bool active = false) {
  uint16_t fill = TFT_DARKGREY;
  if (String(b.command) == "record" && state.recording) fill = TFT_RED;
  if (String(b.command) == "circle" && state.circle) fill = TFT_ORANGE;
  tft.fillRoundRect(b.x, b.y, b.w, b.h, 8, fill);
  tft.drawRoundRect(b.x, b.y, b.w, b.h, 8, TFT_WHITE);
  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(TFT_WHITE, fill);
  tft.drawString(b.label, b.x + b.w / 2, b.y + b.h / 2, 2);
}

void drawMiniMeters() {
  const int startX = 10;
  const int y = 106;
  const int meterW = 70;
  const int meterH = 6;
  const int gap = 7;
  for (int i = 0; i < 4; i++) {
    int x = startX + i * (meterW + gap);
    float db = constrain(state.meters[i], -60.0f, 0.0f);
    int fill = (int)((db + 60.0f) / 60.0f * meterW);
    uint16_t color = TFT_GREEN;
    if (db > -12.0f) color = TFT_YELLOW;
    if (db > -6.0f) color = TFT_RED;
    tft.drawRoundRect(x, y, meterW, meterH, 2, TFT_DARKGREY);
    if (fill > 0) tft.fillRoundRect(x + 1, y + 1, max(1, fill - 2), meterH - 2, 1, color);
  }
}

void drawScreen() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("FILMSET REMOTE", 10, 8, 2);

  if (!state.online) {
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.drawString("RECORDER OFFLINE", 10, 32, 2);
  } else {
    tft.setTextColor(state.recording ? TFT_RED : TFT_GREEN, TFT_BLACK);
    tft.drawString(state.recording ? "RECORDING" : "READY", 10, 32, 2);
  }

  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("R " + state.roll + "   S " + state.scene + "   T " + String(state.take) + (state.circle ? " *" : ""), 10, 58, 2);

  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(state.recording ? TFT_RED : TFT_WHITE, TFT_BLACK);
  tft.drawString(elapsedText(state.elapsed), 160, 88, 4);
  drawMiniMeters();

  for (int i = 0; i < BUTTON_COUNT; i++) drawButton(buttons[i]);

  tft.setTextDatum(BL_DATUM);
  tft.setTextColor(state.xruns > 0 ? TFT_ORANGE : TFT_DARKGREY, TFT_BLACK);
  tft.drawString("WiFi " + String(WiFi.RSSI()) + " dBm  XRUN " + String(state.xruns) + " DROP " + String(state.droppedBlocks), 8, 239, 1);
}

bool readTouch(int &sx, int &sy) {
  if (!ts.touched()) return false;
  TS_Point p = ts.getPoint();

  // Calibration values are starting points for a common CYD.
  // Run a touch calibration for your board and adjust these four numbers.
  int x = map(p.x, 200, 3800, 0, 320);
  int y = map(p.y, 240, 3800, 0, 240);

  // Firmware UI is landscape; rotate touch coordinates to match rotation 1.
  sx = y;
  sy = 320 - x;
  sx = constrain(sx, 0, 319);
  sy = constrain(sy, 0, 239);
  return true;
}

void handleTouch() {
  int x, y;
  if (!readTouch(x, y)) return;

  for (int i = 0; i < BUTTON_COUNT; i++) {
    const Button& b = buttons[i];
    if (x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h) {
      sendCommand(b.command);
      delay(250);
      return;
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);

  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Connecting WiFi...", 10, 10, 2);

  touchSPI.begin(XPT2046_CLK, XPT2046_MISO, XPT2046_MOSI, XPT2046_CS);
  ts.begin(touchSPI);
  ts.setRotation(1);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 15000) {
    delay(250);
  }

  pollStatus();
  drawScreen();
}

void loop() {
  handleTouch();
  if (millis() - lastPoll > 500) {
    lastPoll = millis();
    pollStatus();
  }
  if (millis() - lastDraw > 500) {
    lastDraw = millis();
    drawScreen();
  }
  delay(10);
}
