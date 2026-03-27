/*
 * MINEBOT-Q — STM32 Sensor Reader Firmware
 * Arduino UNO Q (STM32 MCU side)
 *
 * Reads MQ-4, MQ-7, MQ-135 gas sensors via ADC at 10 Hz
 * Sends JSON packets over UART to QRB2210 Linux MPU
 * Implements purge cycle: pump reversal every 5 min for 3 sec (D7)
 */

#include <math.h>

// --- Pin definitions ---
#define MQ4_PIN   A0
#define MQ7_PIN   A1
#define MQ135_PIN A2
#define PUMP_PIN  7

// --- Timing ---
#define GAS_INTERVAL_MS   100   // 10 Hz
#define PURGE_INTERVAL_MS 300000 // 5 minutes
#define PURGE_DURATION_MS  3000  // 3 seconds

// --- MQ sensor calibration (Steinhart-Hart style power-law) ---
// ppm = A * (Rs/R0)^B
// Rs/R0 approximated from ADC: ratio = (1023.0 - adc) / adc
// Coefficients tuned per datasheet curves
struct MQCalibration {
  float a;
  float b;
  float r0;  // sensor resistance in clean air (kohm)
  float rl;  // load resistor (kohm)
};

static const MQCalibration MQ4_CAL  = { 1012.7f, -2.786f, 20.0f, 10.0f };
static const MQCalibration MQ7_CAL  = {  99.042f, -1.518f, 27.0f, 10.0f };
static const MQCalibration MQ135_CAL = { 110.47f, -2.862f, 76.63f, 10.0f };

// --- State ---
unsigned long lastGasRead = 0;
unsigned long lastPurge   = 0;
bool purging = false;
unsigned long purgeStart = 0;

// Latest gas values
float mq4_ppm   = 0;
float mq7_ppm   = 0;
float mq135_ppm = 0;

void setup() {
  Serial.begin(115200);

  // Pump pin
  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, LOW);

  lastPurge = millis();
}

float adcToPpm(int adcRaw, const MQCalibration &cal) {
  if (adcRaw <= 0) return NAN;
  float vout = adcRaw * (3.3f / 4095.0f); // STM32 12-bit ADC, 3.3V ref
  float rs = cal.rl * (3.3f - vout) / vout;
  float ratio = rs / cal.r0;
  if (ratio <= 0) return NAN;
  float ppm = cal.a * pow(ratio, cal.b);
  return (ppm < 0 || isnan(ppm)) ? NAN : ppm;
}

void readGasSensors() {
  int raw4   = analogRead(MQ4_PIN);
  int raw7   = analogRead(MQ7_PIN);
  int raw135 = analogRead(MQ135_PIN);

  mq4_ppm   = adcToPpm(raw4, MQ4_CAL);
  mq7_ppm   = adcToPpm(raw7, MQ7_CAL);
  mq135_ppm = adcToPpm(raw135, MQ135_CAL);
}

void sendJSON() {
  unsigned long ts = millis();

  Serial.print("{\"mq4\":");
  Serial.print(isnan(mq4_ppm) ? 0 : mq4_ppm, 1);
  Serial.print(",\"mq7\":");
  Serial.print(isnan(mq7_ppm) ? 0 : mq7_ppm, 1);
  Serial.print(",\"mq135\":");
  Serial.print(isnan(mq135_ppm) ? 0 : mq135_ppm, 1);
  Serial.print(",\"ts\":");
  Serial.print(ts);
  Serial.println("}");
}

void handlePurge(unsigned long now) {
  if (purging) {
    if (now - purgeStart >= PURGE_DURATION_MS) {
      digitalWrite(PUMP_PIN, LOW);
      purging = false;
    }
  } else {
    if (now - lastPurge >= PURGE_INTERVAL_MS) {
      digitalWrite(PUMP_PIN, HIGH);
      purging = true;
      purgeStart = now;
      lastPurge = now;
    }
  }
}

void loop() {
  unsigned long now = millis();

  // Gas sensors at 10 Hz + send JSON
  if (now - lastGasRead >= GAS_INTERVAL_MS) {
    lastGasRead = now;
    readGasSensors();
    sendJSON();
  }

  // Purge cycle
  handlePurge(now);
}
