/**
 * @file    encoders.cpp
 * @brief   Implémentation des encodeurs.
 *
 * - ISR ultra-courtes en IRAM_ATTR : lecture de la voie B pour déduire le sens.
 * - Compteurs volatile int32_t (atomiques sur ESP32).
 * - Vitesse calculée par fenêtre fixe + filtre passe-bas (alpha = 0.3).
 */
#include "encoders.h"
#include "pins.h"
#include "config.h"

// ----------------------------------------------------------------------------
//   Variables internes
// ----------------------------------------------------------------------------
static volatile int32_t s_ticsLeft  = 0;
static volatile int32_t s_ticsRight = 0;

// État pour le calcul de vitesse
static int32_t  s_lastTicsLeft   = 0;
static int32_t  s_lastTicsRight  = 0;
static uint32_t s_lastSpeedTime  = 0;
static float    s_speedLeftCmS   = 0.0f;
static float    s_speedRightCmS  = 0.0f;

// État pour la détection de blocage
static uint32_t s_stallStartMs   = 0;
static int32_t  s_stallLastL     = 0;
static int32_t  s_stallLastR     = 0;

static const float kCmPerTic =
    WHEEL_CIRCUMFERENCE_CM / static_cast<float>(ENCODER_TICS_PER_REV);

// ----------------------------------------------------------------------------
//   ISR : lecture du sens via la voie B
// ----------------------------------------------------------------------------
static void IRAM_ATTR isrLeftA() {
    // Convention : si voie B HIGH au front montant de A → roue avance.
    if (digitalRead(ENC_G_CH_B) == HIGH) {
        s_ticsLeft += ENCODER_INVERT_LEFT ? -1 : +1;
    } else {
        s_ticsLeft += ENCODER_INVERT_LEFT ? +1 : -1;
    }
}

static void IRAM_ATTR isrRightA() {
    if (digitalRead(ENC_D_CH_B) == HIGH) {
        s_ticsRight += ENCODER_INVERT_RIGHT ? -1 : +1;
    } else {
        s_ticsRight += ENCODER_INVERT_RIGHT ? +1 : -1;
    }
}

// ----------------------------------------------------------------------------
//   API publique
// ----------------------------------------------------------------------------
void encodersInit() {
    pinMode(ENC_G_CH_A, INPUT);
    pinMode(ENC_G_CH_B, INPUT);
    pinMode(ENC_D_CH_A, INPUT);
    pinMode(ENC_D_CH_B, INPUT);

    attachInterrupt(digitalPinToInterrupt(ENC_G_CH_A), isrLeftA,  RISING);
    attachInterrupt(digitalPinToInterrupt(ENC_D_CH_A), isrRightA, RISING);

    encoderResetCounts();
    s_lastSpeedTime = millis();
}

int32_t encoderLeftCount()  { return s_ticsLeft;  }
int32_t encoderRightCount() { return s_ticsRight; }

void encoderResetCounts() {
    noInterrupts();
    s_ticsLeft  = 0;
    s_ticsRight = 0;
    interrupts();
    s_lastTicsLeft  = 0;
    s_lastTicsRight = 0;
    s_speedLeftCmS  = 0.0f;
    s_speedRightCmS = 0.0f;
}

float encoderLeftDistanceCm()  { return s_ticsLeft  * kCmPerTic; }
float encoderRightDistanceCm() { return s_ticsRight * kCmPerTic; }

float encoderLeftSpeedCmPerSec()  { return s_speedLeftCmS;  }
float encoderRightSpeedCmPerSec() { return s_speedRightCmS; }

void encoderUpdateSpeeds() {
    const uint32_t now = millis();
    const uint32_t dt_ms = now - s_lastSpeedTime;
    if (dt_ms < ENCODER_SPEED_WINDOW_MS) return;

    // Snapshot atomique des compteurs
    noInterrupts();
    const int32_t tL = s_ticsLeft;
    const int32_t tR = s_ticsRight;
    interrupts();

    const float dt = dt_ms * 1e-3f;
    const float vL = (tL - s_lastTicsLeft)  * kCmPerTic / dt;
    const float vR = (tR - s_lastTicsRight) * kCmPerTic / dt;

    // Filtre passe-bas exponentiel : lisse les tics manquants
    const float alpha = 0.3f;
    s_speedLeftCmS  = alpha * vL + (1.0f - alpha) * s_speedLeftCmS;
    s_speedRightCmS = alpha * vR + (1.0f - alpha) * s_speedRightCmS;

    s_lastTicsLeft  = tL;
    s_lastTicsRight = tR;
    s_lastSpeedTime = now;
}

bool encoderDetectStall(int pwm_left, int pwm_right) {
    const uint32_t now = millis();
    const int32_t  cL = s_ticsLeft;
    const int32_t  cR = s_ticsRight;

    const bool driving = (abs(pwm_left)  > 100) || (abs(pwm_right) > 100);
    const bool noTics  = (cL == s_stallLastL) && (cR == s_stallLastR);

    if (driving && noTics) {
        if (s_stallStartMs == 0) s_stallStartMs = now;
        if (now - s_stallStartMs >= STALL_DETECT_DURATION_MS) {
            return true;
        }
    } else {
        s_stallStartMs = 0;
        s_stallLastL = cL;
        s_stallLastR = cR;
    }
    return false;
}
