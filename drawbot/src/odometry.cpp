/**
 * @file    odometry.cpp
 * @brief   Implémentation de l'odométrie (modèle différentiel).
 *
 * Algorithme "midpoint" : on évalue cos/sin à la moyenne entre l'angle
 * avant et l'angle après le pas — bien plus précis qu'un simple Euler
 * pour les arcs de cercle.
 *
 * Fusion gyro : filtre complémentaire θ = α·(θ + ωz·dt) + (1-α)·θ_enc
 */
#include "odometry.h"
#include "encoders.h"
#include "imu.h"
#include "config.h"

// ----------------------------------------------------------------------------
//   Variables d'état
// ----------------------------------------------------------------------------
static float    s_x = 0.0f;
static float    s_y = 0.0f;
static float    s_theta_rad = 0.0f;

static float    s_linear_speed = 0.0f;
static float    s_angular_speed_dps = 0.0f;

static float    s_lastDistLeft  = 0.0f;
static float    s_lastDistRight = 0.0f;
static uint32_t s_lastUpdateMs  = 0;

// ----------------------------------------------------------------------------
//   API
// ----------------------------------------------------------------------------
void odometryInit() {
    odometryReset();
    s_lastUpdateMs = millis();
}

void odometryReset() {
    s_x = s_y = 0.0f;
    s_theta_rad = 0.0f;
    s_linear_speed = 0.0f;
    s_angular_speed_dps = 0.0f;
    s_lastDistLeft  = encoderLeftDistanceCm();
    s_lastDistRight = encoderRightDistanceCm();
    s_lastUpdateMs  = millis();
}

void odometrySetPose(float x, float y, float theta_deg) {
    s_x = x; s_y = y;
    s_theta_rad = theta_deg * (PI / 180.0f);
    s_lastDistLeft  = encoderLeftDistanceCm();
    s_lastDistRight = encoderRightDistanceCm();
}

void odometryUpdate() {
    const uint32_t now = millis();
    const float dt = (now - s_lastUpdateMs) * 1e-3f;
    if (dt <= 0.0f) return;
    s_lastUpdateMs = now;

    const float distLeft  = encoderLeftDistanceCm();
    const float distRight = encoderRightDistanceCm();
    const float dL = distLeft  - s_lastDistLeft;
    const float dR = distRight - s_lastDistRight;
    s_lastDistLeft  = distLeft;
    s_lastDistRight = distRight;

    const float dDist     = (dL + dR) * 0.5f;
    const float dThetaEnc = (dR - dL) / WHEEL_BASE_CM;   // rad

    // Fusion complémentaire avec gyroscope (axe Z) si disponible.
    float dTheta = dThetaEnc;
    float gx, gy, gz;
    if (imuReadGyro(gx, gy, gz)) {
        const float dThetaGyro = gz * (PI / 180.0f) * dt;   // rad
        dTheta = ODOMETRY_GYRO_ALPHA * dThetaGyro
               + (1.0f - ODOMETRY_GYRO_ALPHA) * dThetaEnc;
    }

    // Midpoint : cos/sin à mi-pas
    const float midTheta = s_theta_rad + dTheta * 0.5f;
    s_x += dDist * cosf(midTheta);
    s_y += dDist * sinf(midTheta);
    s_theta_rad += dTheta;

    // Normalisation dans (-π, π]
    while (s_theta_rad >  PI) s_theta_rad -= 2.0f * PI;
    while (s_theta_rad <= -PI) s_theta_rad += 2.0f * PI;

    // Vitesses estimées
    s_linear_speed      = dDist / dt;
    s_angular_speed_dps = dTheta * (180.0f / PI) / dt;
}

float odometryGetX()     { return s_x; }
float odometryGetY()     { return s_y; }
float odometryGetTheta() { return s_theta_rad * (180.0f / PI); }
float odometryGetLinearSpeed()  { return s_linear_speed; }
float odometryGetAngularSpeed() { return s_angular_speed_dps; }
