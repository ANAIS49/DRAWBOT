/**
 * @file    magnetometer.h
 * @brief   Driver bas niveau du LIS3MDL (magnétomètre 3 axes I²C).
 *
 * Pas de bibliothèque externe : registres lus directement.
 * Adresse 0x1E, ±4 gauss, mode UHP continu @10 Hz.
 *
 * Calibration "hard-iron" par enregistrement min/max sur 360°.
 */
#pragma once

#include <Arduino.h>

/// Initialise le LIS3MDL. Vérifie WHO_AM_I.
bool magInit();

/// Lit les valeurs brutes 16 bits (LSB).
bool magReadRaw(int16_t &mx, int16_t &my, int16_t &mz);

/// Lit les valeurs en µT après application des offsets/gains de calibration.
bool magReadCalibrated(float &mx, float &my, float &mz);

/**
 * @brief Calcule le cap magnétique horizontal.
 * @return cap en degrés dans [0, 360), 0 = Nord, 90 = Est, 180 = Sud, 270 = Ouest.
 *
 * @warning Suppose le robot à plat (pas de compensation d'inclinaison ici).
 */
float magGetHeading();

/**
 * @brief Routine de calibration hard-iron : tourner le robot à 360°
 *        pendant durationMs et enregistrer min/max sur chaque axe.
 *        L'utilisateur (ou le firmware) doit faire tourner le robot.
 */
void magCalibrate(uint16_t durationMs);

/// Force des offsets/gains de calibration (par exemple chargés depuis flash).
void magSetOffsets(float ox, float oy, float oz);
void magSetScales (float sx, float sy, float sz);

/// Retourne les offsets/gains courants (pour persistance).
void magGetOffsets(float &ox, float &oy, float &oz);
void magGetScales (float &sx, float &sy, float &sz);
