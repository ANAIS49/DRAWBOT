/**
 * @file    control.cpp
 * @brief   Implémentation de l'asservissement cascade.
 */
#include "control.h"
#include "config.h"
#include "pid.h"
#include "motors.h"
#include "encoders.h"
#include "odometry.h"

// ----------------------------------------------------------------------------
//   PIDs internes
// ----------------------------------------------------------------------------
static PID s_pidSpeedLeft (PID_SPEED_KP, PID_SPEED_KI, PID_SPEED_KD);
static PID s_pidSpeedRight(PID_SPEED_KP, PID_SPEED_KI, PID_SPEED_KD);
static PID s_pidDistance  (PID_DISTANCE_KP, PID_DISTANCE_KI, PID_DISTANCE_KD);
static PID s_pidHeading   (PID_HEADING_KP,  PID_HEADING_KI,  PID_HEADING_KD);

// ----------------------------------------------------------------------------
//   État interne
// ----------------------------------------------------------------------------
static bool     s_poseMode = false;     ///< true si setPoseTarget actif
static float    s_targetDistanceCm = 0.0f;
static float    s_targetHeadingDeg = 0.0f;
static float    s_startDistanceCm  = 0.0f; ///< intégrale de distance au début
static float    s_maxSpeedCms      = 10.0f;

static float    s_lastWheelV_left  = 0.0f;
static float    s_lastWheelV_right = 0.0f;

static uint32_t s_lastSpeedUpdateMs = 0;
static uint32_t s_lastPoseUpdateMs  = 0;

// PWM appliqués (utiles pour la détection de stall et les rapports)
static int      s_lastPwmLeft  = 0;
static int      s_lastPwmRight = 0;

// ----------------------------------------------------------------------------
//   Helpers
// ----------------------------------------------------------------------------
/// Renvoie un angle ramené dans (-180, 180]
static float wrapAngleDeg(float a) {
    while (a >  180.0f) a -= 360.0f;
    while (a <= -180.0f) a += 360.0f;
    return a;
}

/// Distance moyenne parcourue (au sens absolu) depuis le reset des encodeurs
static float traveledDistanceCm() {
    return 0.5f * (encoderLeftDistanceCm() + encoderRightDistanceCm());
}

// ----------------------------------------------------------------------------
//   Initialisation
// ----------------------------------------------------------------------------
void controlInit() {
    // Saturation de sortie : -1023..+1023 (PWM)
    s_pidSpeedLeft .setOutputLimits(-MOTOR_PWM_MAX,  MOTOR_PWM_MAX);
    s_pidSpeedRight.setOutputLimits(-MOTOR_PWM_MAX,  MOTOR_PWM_MAX);
    // Anti-windup : on borne l'intégrale à la moitié de la plage PWM
    s_pidSpeedLeft .setIntegralLimits(-MOTOR_PWM_MAX / 2.0f,  MOTOR_PWM_MAX / 2.0f);
    s_pidSpeedRight.setIntegralLimits(-MOTOR_PWM_MAX / 2.0f,  MOTOR_PWM_MAX / 2.0f);

    s_pidDistance.setOutputLimits(-MAX_LINEAR_SPEED_CM_S,  MAX_LINEAR_SPEED_CM_S);
    s_pidDistance.setIntegralLimits(-MAX_LINEAR_SPEED_CM_S, MAX_LINEAR_SPEED_CM_S);

    s_pidHeading.setOutputLimits(-MAX_ANGULAR_SPEED_DPS,  MAX_ANGULAR_SPEED_DPS);
    s_pidHeading.setIntegralLimits(-MAX_ANGULAR_SPEED_DPS, MAX_ANGULAR_SPEED_DPS);

    s_lastSpeedUpdateMs = millis();
    s_lastPoseUpdateMs  = millis();
}

// ----------------------------------------------------------------------------
//   Niveau bas : consignes vitesse roues
// ----------------------------------------------------------------------------
void setWheelSpeeds(float v_left_cms, float v_right_cms) {
    s_poseMode = false;   // mode manuel
    s_lastWheelV_left  = v_left_cms;
    s_lastWheelV_right = v_right_cms;
    s_pidSpeedLeft .setSetpoint(v_left_cms);
    s_pidSpeedRight.setSetpoint(v_right_cms);
}

// ----------------------------------------------------------------------------
//   Niveau haut : consignes (v, ω)
// ----------------------------------------------------------------------------
void setLinearAngular(float v_cms, float omega_dps) {
    const float omega_rps = omega_dps * (PI / 180.0f);
    const float halfBaseCm = WHEEL_BASE_CM * 0.5f;
    const float vL = v_cms - omega_rps * halfBaseCm;
    const float vR = v_cms + omega_rps * halfBaseCm;
    setWheelSpeeds(vL, vR);
}

// ----------------------------------------------------------------------------
//   Mode pose target
// ----------------------------------------------------------------------------
void setPoseTarget(float target_distance_cm,
                   float target_heading_deg,
                   float max_speed_cms) {
    s_poseMode          = true;
    s_targetDistanceCm  = target_distance_cm;
    s_targetHeadingDeg  = target_heading_deg;
    s_startDistanceCm   = traveledDistanceCm();
    s_maxSpeedCms       = max_speed_cms;

    s_pidDistance.reset();
    s_pidHeading .reset();
}

void controlAbort() {
    s_poseMode = false;
    setWheelSpeeds(0.0f, 0.0f);
    motorsStop();
    s_pidSpeedLeft .reset();
    s_pidSpeedRight.reset();
}

bool controlIsBusy() { return s_poseMode; }

// ----------------------------------------------------------------------------
//   Mise à jour périodique
// ----------------------------------------------------------------------------
void controlUpdate() {
    const uint32_t now = millis();

    // ------------------------------------------------------------------
    // Boucle haut niveau (50 Hz) : si une cible de pose est définie,
    // on génère (v, ω) à partir des erreurs distance/cap.
    // ------------------------------------------------------------------
    if (s_poseMode && (now - s_lastPoseUpdateMs >= ODOMETRY_PERIOD_MS)) {
        const float dt = (now - s_lastPoseUpdateMs) * 1e-3f;
        s_lastPoseUpdateMs = now;

        const float traveled = traveledDistanceCm() - s_startDistanceCm;
        const float distError = s_targetDistanceCm - traveled;
        const float headError = wrapAngleDeg(s_targetHeadingDeg - odometryGetTheta());

        s_pidDistance.setSetpoint(s_targetDistanceCm);
        s_pidHeading .setSetpoint(s_targetHeadingDeg);
        // Sortie distance : on lui passe la "mesure" = traveled depuis start
        float v = s_pidDistance.compute(traveled, dt);
        float w = s_pidHeading .compute(odometryGetTheta(), dt);

        // Saturation par max_speed externe (paramètre primitive)
        if (v >  s_maxSpeedCms) v =  s_maxSpeedCms;
        if (v < -s_maxSpeedCms) v = -s_maxSpeedCms;

        // Évite les valeurs absurdes lorsque distError ≈ 0
        (void)distError; (void)headError;

        const float omega_rps = w * (PI / 180.0f);
        const float halfBaseCm = WHEEL_BASE_CM * 0.5f;
        s_lastWheelV_left  = v - omega_rps * halfBaseCm;
        s_lastWheelV_right = v + omega_rps * halfBaseCm;
        s_pidSpeedLeft .setSetpoint(s_lastWheelV_left);
        s_pidSpeedRight.setSetpoint(s_lastWheelV_right);
    }

    // ------------------------------------------------------------------
    // Boucle bas niveau (100 Hz) : asservissement de vitesse de chaque roue
    // ------------------------------------------------------------------
    if (now - s_lastSpeedUpdateMs >= CONTROL_PERIOD_MS) {
        const float dt = (now - s_lastSpeedUpdateMs) * 1e-3f;
        s_lastSpeedUpdateMs = now;

        // Refresh des vitesses mesurées
        encoderUpdateSpeeds();
        const float vL = encoderLeftSpeedCmPerSec();
        const float vR = encoderRightSpeedCmPerSec();

        const float pwmL = s_pidSpeedLeft .compute(vL, dt);
        const float pwmR = s_pidSpeedRight.compute(vR, dt);

        s_lastPwmLeft  = (int)pwmL;
        s_lastPwmRight = (int)pwmR;
        motorsSetSpeeds(s_lastPwmLeft, s_lastPwmRight);

        // Détection blocage roues (sécurité)
        if (encoderDetectStall(s_lastPwmLeft, s_lastPwmRight)) {
            controlAbort();
        }
    }
}

// ----------------------------------------------------------------------------
//   Tuning des PIDs
// ----------------------------------------------------------------------------
void setSpeedPIDGains(float kp, float ki, float kd) {
    s_pidSpeedLeft .setGains(kp, ki, kd);
    s_pidSpeedRight.setGains(kp, ki, kd);
}
void setDistancePIDGains(float kp, float ki, float kd) {
    s_pidDistance.setGains(kp, ki, kd);
}
void setHeadingPIDGains(float kp, float ki, float kd) {
    s_pidHeading.setGains(kp, ki, kd);
}

void getSpeedPIDGains(float &kp, float &ki, float &kd) {
    s_pidSpeedLeft.getGains(kp, ki, kd);
}
void getDistancePIDGains(float &kp, float &ki, float &kd) {
    s_pidDistance.getGains(kp, ki, kd);
}
void getHeadingPIDGains(float &kp, float &ki, float &kd) {
    s_pidHeading.getGains(kp, ki, kd);
}
