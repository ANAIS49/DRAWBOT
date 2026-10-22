/**
 * @file    main.cpp  (équivalent de drawbot.ino sur PlatformIO)
 * @brief   Point d'entrée du firmware Drawbot.
 *
 * Initialise les modules dans l'ordre, puis enchaîne dans loop() :
 *   - asservissement bas niveau (100 Hz)
 *   - odométrie + boucle haut niveau (50 Hz)
 *   - télémétrie Teleplot (10 Hz)
 *   - lecture des commandes série (en continu)
 *
 * Aucune communication WiFi/BLE pour cette version : tout passe par le
 * port série à 115200 bauds.
 */
#include <Arduino.h>
#include <Wire.h>

#include "pins.h"
#include "config.h"
#include "motors.h"
#include "encoders.h"
#include "imu.h"
#include "magnetometer.h"
#include "odometry.h"
#include "control.h"
#include "primitives.h"
#include "sequences.h"
#include "commands.h"

// ----------------------------------------------------------------------------
//   setup()
// ----------------------------------------------------------------------------
void setup() {
    Serial.begin(SERIAL_BAUD_RATE);
    while (!Serial && millis() < 3000) { /* attendre l'host USB max 3 s */ }

    Serial.println();
    Serial.printf("[INFO] Drawbot firmware v%s starting...\n", FIRMWARE_VERSION);

    // --- I²C 400 kHz ---
    Wire.begin(SDA_PIN, SCL_PIN);
    Wire.setClock(400000);

    // --- LEDs utilisateur ---
    pinMode(LEDU1, OUTPUT);
    pinMode(LEDU2, OUTPUT);
    digitalWrite(LEDU1, LOW);
    digitalWrite(LEDU2, LOW);

    // --- Modules dans l'ordre des dépendances ---
    motorsInit();
    encodersInit();

    if (!imuInit()) Serial.println(F("[ERR] IMU init failed (LSM6DS3 muet ou WHO_AM_I incorrect)"));
    else            Serial.println(F("[OK]  IMU init"));

    if (!magInit()) Serial.println(F("[ERR] MAG init failed (LIS3MDL muet ou WHO_AM_I incorrect)"));
    else            Serial.println(F("[OK]  MAG init"));

    odometryInit();
    controlInit();
    commandsInit();

    // --- Calibration gyroscope au démarrage (robot censé être immobile) ---
    Serial.println(F("[INFO] Calibrating gyro... keep robot still 5 s"));
    imuCalibrateGyro();
    Serial.println(F("[OK]  Gyro calibrated"));

    // --- LED de statut "prête" ---
    digitalWrite(LEDU1, HIGH);
    Serial.println(F("[OK]  Drawbot ready. Type HELP for commands."));
}

// ----------------------------------------------------------------------------
//   loop()
// ----------------------------------------------------------------------------
void loop() {
    static uint32_t last_control   = 0;
    static uint32_t last_odom      = 0;
    static uint32_t last_telemetry = 0;
    const  uint32_t now = millis();

    // Asservissement de vitesse roues à 100 Hz
    if (now - last_control >= CONTROL_PERIOD_MS) {
        controlUpdate();
        last_control = now;
    }

    // Odométrie + asservissement haut niveau à 50 Hz
    if (now - last_odom >= ODOMETRY_PERIOD_MS) {
        odometryUpdate();
        last_odom = now;
    }

    // Télémétrie Teleplot à 10 Hz
    if (now - last_telemetry >= TELEMETRY_PERIOD_MS) {
        sendTelemetry();
        last_telemetry = now;
    }

    // Commandes série
    commandsProcess();
}
