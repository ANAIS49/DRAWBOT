/**
 * @file    commands.cpp
 * @brief   Implémentation du parser de commandes série.
 *
 * Buffer fixe de 128 octets pour respecter la contrainte "pas de String
 * dynamique". Les paramètres sont parsés à coup de strtok_r/strtof.
 */
#include "commands.h"
#include "config.h"
#include "pins.h"
#include "motors.h"
#include "encoders.h"
#include "imu.h"
#include "magnetometer.h"
#include "odometry.h"
#include "control.h"
#include "primitives.h"
#include "sequences.h"

#include <Arduino.h>
#include <string.h>
#include <stdlib.h>

// ----------------------------------------------------------------------------
//   Buffer ligne
// ----------------------------------------------------------------------------
static const size_t kLineMax = 128;
static char     s_line[kLineMax];
static size_t   s_lineLen = 0;

// ----------------------------------------------------------------------------
//   Helpers
// ----------------------------------------------------------------------------
static char* nextToken(char** save) {
    return strtok_r(nullptr, " \t\r\n", save);
}

static bool getFloat(char** save, float &out) {
    char* tok = nextToken(save);
    if (!tok) return false;
    out = strtof(tok, nullptr);
    return true;
}

static bool getInt(char** save, int &out) {
    char* tok = nextToken(save);
    if (!tok) return false;
    out = atoi(tok);
    return true;
}

// ----------------------------------------------------------------------------
//   Tests d'usine (commandes TEST_*)
// ----------------------------------------------------------------------------
static void testMotors() {
    Serial.println(F("[INFO] Test moteurs : avant 1s, arrière 1s, chaque côté"));
    motorsSetSpeeds( 600,  600); delay(1000);
    motorsSetSpeeds(-600, -600); delay(1000);
    motorsSetSpeeds( 600,    0); delay(1000);
    motorsSetSpeeds(   0,  600); delay(1000);
    motorsStop();
    Serial.println(F("[OK] Test moteurs terminé"));
}

static void testEncoders() {
    Serial.println(F("[INFO] Affichage des tics encodeurs pendant 5 s"));
    const uint32_t t0 = millis();
    while (millis() - t0 < 5000) {
        Serial.printf("[DATA] ENC %ld %ld\n",
                      (long)encoderLeftCount(), (long)encoderRightCount());
        delay(200);
    }
    Serial.println(F("[OK] Test encodeurs terminé"));
}

static void testImu() {
    Serial.println(F("[INFO] IMU : ax ay az gx gy gz pendant 5 s"));
    const uint32_t t0 = millis();
    while (millis() - t0 < 5000) {
        float a[3], g[3];
        if (imuReadAll(a, g)) {
            Serial.printf("[DATA] IMU %.3f %.3f %.3f %.2f %.2f %.2f\n",
                          a[0], a[1], a[2], g[0], g[1], g[2]);
        }
        delay(100);
    }
    Serial.println(F("[OK] Test IMU terminé"));
}

static void testMag() {
    Serial.println(F("[INFO] Cap magnétomètre pendant 5 s"));
    const uint32_t t0 = millis();
    while (millis() - t0 < 5000) {
        Serial.printf("[DATA] HEADING %.1f\n", magGetHeading());
        delay(100);
    }
    Serial.println(F("[OK] Test mag terminé"));
}

static void testPwmSweep() {
    Serial.println(F("[INFO] PWM sweep 0 → 1023 par pas de 50"));
    for (int p = 0; p <= 1000; p += 50) {
        motorsSetSpeeds(p, p);
        delay(500);
        encoderUpdateSpeeds();
        Serial.printf("[DATA] SWEEP pwm=%d vL=%.2f vR=%.2f\n", p,
                      encoderLeftSpeedCmPerSec(),
                      encoderRightSpeedCmPerSec());
    }
    motorsStop();
    Serial.println(F("[OK] PWM sweep terminé"));
}

static void testSquare() {
    Serial.println(F("[INFO] Carré 20 cm"));
    const float xStart = odometryGetX();
    const float yStart = odometryGetY();
    for (int i = 0; i < 4; i++) {
        moveForward(20.0f);
        turnLeft(90.0f);
    }
    Serial.printf("[OK] Carré terminé. Erreur retour : (%.2f, %.2f) cm\n",
                  odometryGetX() - xStart, odometryGetY() - yStart);
}

static void testTurn360() {
    Serial.println(F("[INFO] Rotation 360°"));
    const float thetaStart = odometryGetTheta();
    turnLeft(360.0f);
    Serial.printf("[OK] Rotation terminée. Erreur de fermeture : %.2f °\n",
                  odometryGetTheta() - thetaStart);
}

// ----------------------------------------------------------------------------
//   Listing HELP
// ----------------------------------------------------------------------------
static void cmdHelp() {
    Serial.println(F("[INFO] Commandes disponibles :"));
    Serial.println(F("  -- pilotage --"));
    Serial.println(F("  FORWARD <cm>          BACKWARD <cm>"));
    Serial.println(F("  LEFT <deg>            RIGHT <deg>"));
    Serial.println(F("  STOP                  SETSPEED <pwmL> <pwmR>"));
    Serial.println(F("  -- séquences --"));
    Serial.println(F("  SEQ1 [l1 a1 l2 a2 l3] SEQ2 <radius>   SEQ3 <length>"));
    Serial.println(F("  SQUARES <size> <nb>   ROSACE <r> <petals>   COMPASS <diam>"));
    Serial.println(F("  -- capteurs --"));
    Serial.println(F("  GETPOSE  GETIMU  GETMAG  GETENC  GETBAT"));
    Serial.println(F("  -- calibration --"));
    Serial.println(F("  CALIB_GYRO  CALIB_MAG  RESET_POSE"));
    Serial.println(F("  -- PID tuning --"));
    Serial.println(F("  SETPID_SPEED <kp> <ki> <kd>  SETPID_DIST  SETPID_HEAD  GETPID"));
    Serial.println(F("  -- système --"));
    Serial.println(F("  HELP  PING  VERSION  REBOOT"));
    Serial.println(F("  -- tests --"));
    Serial.println(F("  TEST_MOTORS  TEST_ENCODERS  TEST_IMU  TEST_MAG"));
    Serial.println(F("  TEST_PWM_SWEEP  TEST_SQUARE  TEST_TURN_360"));
}

// ----------------------------------------------------------------------------
//   Dispatch principal d'une ligne
// ----------------------------------------------------------------------------
static void executeLine(char* line) {
    char* save = nullptr;
    char* cmd  = strtok_r(line, " \t\r\n", &save);
    if (!cmd) return;

    // ---- Pilotage ----
    if      (!strcasecmp(cmd, "FORWARD")) {
        float d; if (!getFloat(&save, d)) { Serial.println(F("[ERR] FORWARD <cm>")); return; }
        Serial.printf("[OK] Moving forward %.1f cm\n", d);
        moveForward(d);
        Serial.printf("[OK] Motion complete. Pose: X=%.2f Y=%.2f theta=%.2f\n",
                      odometryGetX(), odometryGetY(), odometryGetTheta());
    }
    else if (!strcasecmp(cmd, "BACKWARD")) {
        float d; if (!getFloat(&save, d)) { Serial.println(F("[ERR] BACKWARD <cm>")); return; }
        moveBackward(d);
        Serial.println(F("[OK] Backward done"));
    }
    else if (!strcasecmp(cmd, "LEFT")) {
        float a; if (!getFloat(&save, a)) { Serial.println(F("[ERR] LEFT <deg>")); return; }
        turnLeft(a);
        Serial.println(F("[OK] Left done"));
    }
    else if (!strcasecmp(cmd, "RIGHT")) {
        float a; if (!getFloat(&save, a)) { Serial.println(F("[ERR] RIGHT <deg>")); return; }
        turnRight(a);
        Serial.println(F("[OK] Right done"));
    }
    else if (!strcasecmp(cmd, "STOP")) {
        controlAbort();
        Serial.println(F("[OK] STOP"));
    }
    else if (!strcasecmp(cmd, "SETSPEED")) {
        int l, r;
        if (!getInt(&save, l) || !getInt(&save, r)) {
            Serial.println(F("[ERR] SETSPEED <pwmL> <pwmR>")); return;
        }
        motorsSetSpeeds(l, r);
        Serial.printf("[OK] PWM L=%d R=%d\n", l, r);
    }

    // ---- Séquences ----
    else if (!strcasecmp(cmd, "SEQ1")) {
        float l1, a1, l2, a2, l3;
        if (getFloat(&save, l1) && getFloat(&save, a1)
         && getFloat(&save, l2) && getFloat(&save, a2)
         && getFloat(&save, l3)) {
            sequenceEscalierCustom(l1, a1, l2, a2, l3);
        } else {
            sequenceEscalier();
        }
        Serial.println(F("[OK] SEQ1 done"));
    }
    else if (!strcasecmp(cmd, "SEQ2")) {
        float r; if (!getFloat(&save, r)) { Serial.println(F("[ERR] SEQ2 <radius>")); return; }
        sequenceCercle(r);
        Serial.println(F("[OK] SEQ2 done"));
    }
    else if (!strcasecmp(cmd, "SEQ3")) {
        float l; if (!getFloat(&save, l)) { Serial.println(F("[ERR] SEQ3 <length>")); return; }
        sequenceFlecheNord(l);
        Serial.println(F("[OK] SEQ3 done"));
    }
    else if (!strcasecmp(cmd, "SQUARES")) {
        float s; int n;
        if (!getFloat(&save, s) || !getInt(&save, n)) {
            Serial.println(F("[ERR] SQUARES <size> <nb>")); return;
        }
        sequenceCarresCircles(s, n);
        Serial.println(F("[OK] SQUARES done"));
    }
    else if (!strcasecmp(cmd, "ROSACE")) {
        float r; int p;
        if (!getFloat(&save, r) || !getInt(&save, p)) {
            Serial.println(F("[ERR] ROSACE <r> <petals>")); return;
        }
        sequenceRosace(r, p);
        Serial.println(F("[OK] ROSACE done"));
    }
    else if (!strcasecmp(cmd, "COMPASS")) {
        float d; if (!getFloat(&save, d)) { Serial.println(F("[ERR] COMPASS <diam>")); return; }
        sequenceRoseDesVents(d);
        Serial.println(F("[OK] COMPASS done"));
    }

    // ---- Capteurs / état ----
    else if (!strcasecmp(cmd, "GETPOSE")) {
        Serial.printf("[DATA] POSE %.2f %.2f %.2f\n",
                      odometryGetX(), odometryGetY(), odometryGetTheta());
    }
    else if (!strcasecmp(cmd, "GETIMU")) {
        float a[3], g[3];
        if (imuReadAll(a, g)) {
            Serial.printf("[DATA] IMU %.3f %.3f %.3f %.2f %.2f %.2f\n",
                          a[0], a[1], a[2], g[0], g[1], g[2]);
        } else {
            Serial.println(F("[ERR] IMU read failed"));
        }
    }
    else if (!strcasecmp(cmd, "GETMAG")) {
        float mx, my, mz;
        if (magReadCalibrated(mx, my, mz)) {
            Serial.printf("[DATA] MAG %.2f %.2f %.2f %.1f\n",
                          mx, my, mz, magGetHeading());
        } else {
            Serial.println(F("[ERR] MAG read failed"));
        }
    }
    else if (!strcasecmp(cmd, "GETENC")) {
        Serial.printf("[DATA] ENC %ld %ld %.2f %.2f\n",
                      (long)encoderLeftCount(), (long)encoderRightCount(),
                      encoderLeftSpeedCmPerSec(), encoderRightSpeedCmPerSec());
    }
    else if (!strcasecmp(cmd, "GETBAT")) {
        // TODO: brancher une mesure réelle (diviseur de tension sur ADC)
        Serial.println(F("[DATA] BAT 5.10"));
    }

    // ---- Calibration ----
    else if (!strcasecmp(cmd, "CALIB_GYRO")) {
        Serial.println(F("[INFO] Garder le robot immobile..."));
        imuCalibrateGyro();
        float ox, oy, oz; imuGetGyroOffsets(ox, oy, oz);
        Serial.printf("[OK] Gyro offsets: %.3f %.3f %.3f\n", ox, oy, oz);
    }
    else if (!strcasecmp(cmd, "CALIB_MAG")) {
        Serial.println(F("[INFO] Calibration mag : rotation 360° (10 s)..."));
        // On pilote la rotation pendant que la routine échantillonne
        setLinearAngular(0.0f, 36.0f);   // 36 °/s ≈ 360°/10 s
        magCalibrate(10000);
        setLinearAngular(0.0f, 0.0f);
        motorsStop();
        Serial.println(F("[OK] CALIB_MAG done"));
    }
    else if (!strcasecmp(cmd, "RESET_POSE")) {
        encoderResetCounts();
        odometryReset();
        Serial.println(F("[OK] Pose reset"));
    }

    // ---- PID tuning ----
    else if (!strcasecmp(cmd, "SETPID_SPEED")) {
        float kp, ki, kd;
        if (!getFloat(&save, kp) || !getFloat(&save, ki) || !getFloat(&save, kd)) {
            Serial.println(F("[ERR] SETPID_SPEED <kp> <ki> <kd>")); return;
        }
        setSpeedPIDGains(kp, ki, kd);
        Serial.println(F("[OK] Speed PID updated"));
    }
    else if (!strcasecmp(cmd, "SETPID_DIST")) {
        float kp, ki, kd;
        if (!getFloat(&save, kp) || !getFloat(&save, ki) || !getFloat(&save, kd)) {
            Serial.println(F("[ERR] SETPID_DIST <kp> <ki> <kd>")); return;
        }
        setDistancePIDGains(kp, ki, kd);
        Serial.println(F("[OK] Distance PID updated"));
    }
    else if (!strcasecmp(cmd, "SETPID_HEAD")) {
        float kp, ki, kd;
        if (!getFloat(&save, kp) || !getFloat(&save, ki) || !getFloat(&save, kd)) {
            Serial.println(F("[ERR] SETPID_HEAD <kp> <ki> <kd>")); return;
        }
        setHeadingPIDGains(kp, ki, kd);
        Serial.println(F("[OK] Heading PID updated"));
    }
    else if (!strcasecmp(cmd, "GETPID")) {
        float kp, ki, kd;
        getSpeedPIDGains(kp, ki, kd);
        Serial.printf("[DATA] PID_SPEED %.2f %.2f %.2f\n", kp, ki, kd);
        getDistancePIDGains(kp, ki, kd);
        Serial.printf("[DATA] PID_DIST  %.2f %.2f %.2f\n", kp, ki, kd);
        getHeadingPIDGains(kp, ki, kd);
        Serial.printf("[DATA] PID_HEAD  %.2f %.2f %.2f\n", kp, ki, kd);
    }

    // ---- Système ----
    else if (!strcasecmp(cmd, "HELP"))    { cmdHelp(); }
    else if (!strcasecmp(cmd, "PING"))    { Serial.println(F("[OK] PONG")); }
    else if (!strcasecmp(cmd, "VERSION")) { Serial.printf("[INFO] Drawbot firmware v%s\n", FIRMWARE_VERSION); }
    else if (!strcasecmp(cmd, "REBOOT"))  { Serial.println(F("[INFO] Reboot...")); delay(50); ESP.restart(); }

    // ---- Tests ----
    else if (!strcasecmp(cmd, "TEST_MOTORS"))    { testMotors(); }
    else if (!strcasecmp(cmd, "TEST_ENCODERS")) { testEncoders(); }
    else if (!strcasecmp(cmd, "TEST_IMU"))      { testImu(); }
    else if (!strcasecmp(cmd, "TEST_MAG"))      { testMag(); }
    else if (!strcasecmp(cmd, "TEST_PWM_SWEEP")){ testPwmSweep(); }
    else if (!strcasecmp(cmd, "TEST_SQUARE"))   { testSquare(); }
    else if (!strcasecmp(cmd, "TEST_TURN_360")) { testTurn360(); }

    else {
        Serial.printf("[ERR] Unknown command: %s (try HELP)\n", cmd);
    }
}

// ----------------------------------------------------------------------------
//   Boucle de réception (non bloquante)
// ----------------------------------------------------------------------------
void commandsInit() {
    s_lineLen = 0;
}

void commandsProcess() {
    while (Serial.available() > 0) {
        const int c = Serial.read();
        if (c < 0) break;
        if (c == '\r') continue;
        if (c == '\n' || s_lineLen >= kLineMax - 1) {
            s_line[s_lineLen] = '\0';
            if (s_lineLen > 0) executeLine(s_line);
            s_lineLen = 0;
            continue;
        }
        s_line[s_lineLen++] = (char)c;
    }
}

// ----------------------------------------------------------------------------
//   Télémétrie Teleplot
// ----------------------------------------------------------------------------
void sendTelemetry() {
    Serial.printf(">x:%.2f\n",      odometryGetX());
    Serial.printf(">y:%.2f\n",      odometryGetY());
    Serial.printf(">theta:%.2f\n",  odometryGetTheta());
    Serial.printf(">speedL:%.2f\n", encoderLeftSpeedCmPerSec());
    Serial.printf(">speedR:%.2f\n", encoderRightSpeedCmPerSec());
    Serial.printf(">heading:%.2f\n", magGetHeading());
}
