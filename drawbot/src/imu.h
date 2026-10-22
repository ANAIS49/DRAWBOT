/**
 * @file    imu.h
 * @brief   Driver bas niveau du LSM6DS3 (accéléromètre + gyroscope I²C).
 *
 * On parle directement aux registres pour bien comprendre le protocole
 * (pas de dépendance à Adafruit_LSM6DS3). Adresse 0x6B, bus I²C @400 kHz.
 *
 * Sensibilités utilisées :
 *   - Accéléro ±2 g  : 0,061 mg/LSB
 *   - Gyro     ±500 dps : 17,50 mdps/LSB
 */
#pragma once

#include <Arduino.h>

/// Initialise l'IMU. Retourne false si WHO_AM_I incorrect ou bus muet.
bool imuInit();

/// Lit l'accéléromètre, valeurs en g.
bool imuReadAccel(float &ax, float &ay, float &az);

/// Lit le gyroscope, valeurs en °/s, après application des offsets calibrés.
bool imuReadGyro(float &gx, float &gy, float &gz);

/**
 * @brief Lit accéléro + gyro en une seule transaction (plus rapide).
 * @param accel  tableau [ax, ay, az] en g
 * @param gyro   tableau [gx, gy, gz] en °/s (offsets retirés)
 */
bool imuReadAll(float* accel, float* gyro);

/**
 * @brief Calibre le gyroscope (robot immobile, 500 échantillons à 104 Hz).
 *        Calcule les offsets gx_offset, gy_offset, gz_offset.
 */
void imuCalibrateGyro();

/// Retourne les offsets de gyroscope mesurés lors de la dernière calibration.
void imuGetGyroOffsets(float &ox, float &oy, float &oz);
