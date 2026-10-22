/**
 * @file    primitives.cpp
 * @brief   Implémentation des primitives de mouvement.
 *
 * Stratégie : on ne se sert pas du PID distance/cap intégré du module
 * control pour les primitives bloquantes — on utilise un asservissement
 * direct sur les vitesses roues, plus prévisible pour les tracés.
 *
 * Les primitives bloquantes appellent ``controlUpdate()`` indirectement
 * via la boucle principale, donc elles doivent être lancées depuis
 * setup() ou depuis le parser de commandes (et non depuis loop() où
 * elles bloqueraient les autres tâches).
 */
#include "primitives.h"
#include "config.h"
#include "control.h"
#include "encoders.h"
#include "odometry.h"
#include "motors.h"
#include "magnetometer.h"

// ----------------------------------------------------------------------------
//   Helpers internes
// ----------------------------------------------------------------------------
static float wrapAngleDeg(float a) {
    while (a >  180.0f) a -= 360.0f;
    while (a <= -180.0f) a += 360.0f;
    return a;
}

/**
 * @brief Pompe la boucle d'asservissement pendant qu'on attend la fin
 *        d'un mouvement (équivalent d'un yield() respectueux du temps réel).
 */
static void pumpControl() {
    controlUpdate();
}

/**
 * @brief Attend que les vitesses roues mesurées descendent sous un seuil
 *        et y restent pendant MOTION_STABLE_DURATION_MS.
 * @return true si la stabilité est atteinte avant le timeout, false sinon.
 */
static bool waitUntilStable(uint32_t timeout_ms) {
    const uint32_t start = millis();
    uint32_t stableStart = 0;
    while (millis() - start < timeout_ms) {
        pumpControl();
        const float vL = encoderLeftSpeedCmPerSec();
        const float vR = encoderRightSpeedCmPerSec();
        if (fabsf(vL) < MOTION_SPEED_TOLERANCE && fabsf(vR) < MOTION_SPEED_TOLERANCE) {
            if (stableStart == 0) stableStart = millis();
            else if (millis() - stableStart >= MOTION_STABLE_DURATION_MS) return true;
        } else {
            stableStart = 0;
        }
        delay(2);
    }
    return false;
}

// ----------------------------------------------------------------------------
//   moveForward / moveBackward
// ----------------------------------------------------------------------------
static bool moveStraight(float distance_cm, float speed_cm_s, bool forward) {
    if (distance_cm < 0.0f) distance_cm = -distance_cm;
    if (distance_cm < 0.01f) return true;

    const float v = (forward ? +1.0f : -1.0f) * fabsf(speed_cm_s);
    const float startDist = 0.5f *
        (encoderLeftDistanceCm() + encoderRightDistanceCm());

    setLinearAngular(v, 0.0f);

    const uint32_t t0 = millis();
    while (millis() - t0 < MOTION_TIMEOUT_MS) {
        pumpControl();
        const float traveled = fabsf(0.5f *
            (encoderLeftDistanceCm() + encoderRightDistanceCm()) - startDist);
        if (traveled >= distance_cm - MOTION_POS_TOLERANCE_CM) {
            break;
        }
        delay(2);
    }
    setLinearAngular(0.0f, 0.0f);
    motorsStop();
    waitUntilStable(1000);
    return true;
}

bool moveForward (float distance_cm, float speed_cm_s) {
    return moveStraight(distance_cm, speed_cm_s, true);
}

bool moveBackward(float distance_cm, float speed_cm_s) {
    return moveStraight(distance_cm, speed_cm_s, false);
}

// ----------------------------------------------------------------------------
//   turnLeft / turnRight (angle relatif, en place)
// ----------------------------------------------------------------------------
static bool turnInPlace(float angle_deg, float speed_dps) {
    if (fabsf(angle_deg) < 0.1f) return true;
    const float startTheta = odometryGetTheta();
    const float targetTheta = wrapAngleDeg(startTheta + angle_deg);
    const float omega = (angle_deg > 0.0f ? +1.0f : -1.0f) * fabsf(speed_dps);

    setLinearAngular(0.0f, omega);

    const uint32_t t0 = millis();
    while (millis() - t0 < MOTION_TIMEOUT_MS) {
        pumpControl();
        const float err = fabsf(wrapAngleDeg(targetTheta - odometryGetTheta()));
        if (err <= MOTION_ANG_TOLERANCE_DEG) break;
        delay(2);
    }
    setLinearAngular(0.0f, 0.0f);
    motorsStop();
    waitUntilStable(1000);
    return true;
}

bool turnLeft (float angle_deg, float speed_dps) { return turnInPlace(+angle_deg, speed_dps); }
bool turnRight(float angle_deg, float speed_dps) { return turnInPlace(-angle_deg, speed_dps); }

// ----------------------------------------------------------------------------
//   turnToHeading
// ----------------------------------------------------------------------------
bool turnToHeading(float target_deg, float tolerance_deg, bool useMagnetometer) {
    const uint32_t t0 = millis();
    while (millis() - t0 < MOTION_TIMEOUT_MS) {
        const float current = useMagnetometer ? magGetHeading()
                                              : odometryGetTheta();
        const float err = wrapAngleDeg(target_deg - current);
        if (fabsf(err) <= tolerance_deg) {
            setLinearAngular(0.0f, 0.0f);
            motorsStop();
            return waitUntilStable(1000);
        }
        // Vitesse proportionnelle, plafonnée
        float omega = err * 4.0f;
        if (omega >  MAX_ANGULAR_SPEED_DPS) omega =  MAX_ANGULAR_SPEED_DPS;
        if (omega < -MAX_ANGULAR_SPEED_DPS) omega = -MAX_ANGULAR_SPEED_DPS;
        setLinearAngular(0.0f, omega);
        pumpControl();
        delay(5);
    }
    setLinearAngular(0.0f, 0.0f);
    motorsStop();
    return false;
}

// ----------------------------------------------------------------------------
//   moveArc : suit un arc de cercle de rayon donné
// ----------------------------------------------------------------------------
bool moveArc(float radius_cm, float angle_deg, float speed_cm_s) {
    if (radius_cm <= 0.01f) return false;
    const float angle_rad = angle_deg * (PI / 180.0f);
    const float arc_length_cm = fabsf(radius_cm * angle_rad);

    // ω et v conjugués pour suivre un cercle de rayon r
    const float v = fabsf(speed_cm_s);
    float omega_dps = (v / radius_cm) * (180.0f / PI);
    if (angle_deg < 0.0f) omega_dps = -omega_dps;

    const float startDist = 0.5f *
        (encoderLeftDistanceCm() + encoderRightDistanceCm());

    setLinearAngular(v, omega_dps);

    const uint32_t t0 = millis();
    while (millis() - t0 < MOTION_TIMEOUT_MS) {
        pumpControl();
        const float traveled = fabsf(0.5f *
            (encoderLeftDistanceCm() + encoderRightDistanceCm()) - startDist);
        if (traveled >= arc_length_cm - MOTION_POS_TOLERANCE_CM) break;
        delay(2);
    }
    setLinearAngular(0.0f, 0.0f);
    motorsStop();
    waitUntilStable(1000);
    return true;
}

// ----------------------------------------------------------------------------
//   Mouvements asynchrones (squelette minimal)
// ----------------------------------------------------------------------------
static struct {
    bool     active;
    float    targetCm;
    float    startCm;
    float    speed;
    uint32_t startMs;
} s_async = {false, 0, 0, 0, 0};

void moveForwardAsync(float distance_cm, float speed_cm_s) {
    s_async.active   = true;
    s_async.targetCm = distance_cm;
    s_async.startCm  = 0.5f * (encoderLeftDistanceCm() + encoderRightDistanceCm());
    s_async.speed    = speed_cm_s;
    s_async.startMs  = millis();
    setLinearAngular(speed_cm_s, 0.0f);
}

bool isMotionComplete() {
    if (!s_async.active) return true;
    const float traveled = fabsf(0.5f *
        (encoderLeftDistanceCm() + encoderRightDistanceCm()) - s_async.startCm);
    if (traveled >= s_async.targetCm - MOTION_POS_TOLERANCE_CM
        || millis() - s_async.startMs >= MOTION_TIMEOUT_MS) {
        setLinearAngular(0.0f, 0.0f);
        motorsStop();
        s_async.active = false;
        return true;
    }
    return false;
}

void stopMotion(bool doBrake) {
    s_async.active = false;
    setLinearAngular(0.0f, 0.0f);
    if (doBrake) motorsStop(); else { motorLeft.coast(); motorRight.coast(); }
}
