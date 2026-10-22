/**
 * @file    odometry.h
 * @brief   Estimation de la pose (X, Y, θ) du robot par odométrie
 *          différentielle, avec fusion optionnelle gyro (filtre
 *          complémentaire).
 *
 * Le repère est fixé au démarrage : X devant, Y à gauche, θ = 0 = X.
 */
#pragma once

#include <Arduino.h>

void  odometryInit();

/**
 * @brief Met à jour la pose à partir des deltas d'encodeurs et,
 *        si disponible, d'un échantillon de gyroscope.
 *        À appeler à fréquence régulière (50 Hz typique).
 */
void  odometryUpdate();

/// Remet la pose à (0, 0, 0).
void  odometryReset();

float odometryGetX();           ///< en cm
float odometryGetY();           ///< en cm
float odometryGetTheta();       ///< en degrés, dans (-180, 180]

float odometryGetLinearSpeed();    ///< cm/s instantané
float odometryGetAngularSpeed();   ///< °/s instantané

/// Force la pose (par exemple après calibration manuelle).
void  odometrySetPose(float x, float y, float theta_deg);
