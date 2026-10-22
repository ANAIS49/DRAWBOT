/**
 * @file    magnetometer.cpp
 * @brief   Implémentation du driver LIS3MDL.
 *
 * Sensibilité ±4 gauss : 6842 LSB/gauss → 1 LSB ≈ 14,6 mgauss.
 * 1 gauss = 100 µT, donc 1 LSB ≈ 1,46 µT.
 */
#include "magnetometer.h"
#include "pins.h"
#include <Wire.h>

// ----------------------------------------------------------------------------
//   Registres LIS3MDL
// ----------------------------------------------------------------------------
#define LIS3_WHO_AM_I        0x0F
#define LIS3_CTRL_REG1       0x20
#define LIS3_CTRL_REG2       0x21
#define LIS3_CTRL_REG3       0x22
#define LIS3_CTRL_REG4       0x23
#define LIS3_OUT_X_L         0x28

#define LIS3_WHO_AM_I_VAL    0x3D

// Sensibilité ±4 gauss (cf. datasheet § 3.1) en µT/LSB
static const float kMagLSBuT = 100.0f / 6842.0f;   // ≈ 0,01462 µT/LSB

// Offsets et gains de calibration (par défaut neutres)
static float s_ox = 0.0f, s_oy = 0.0f, s_oz = 0.0f;   // hard-iron, en µT
static float s_sx = 1.0f, s_sy = 1.0f, s_sz = 1.0f;   // soft-iron simplifié

// ----------------------------------------------------------------------------
//   Helpers I²C
// ----------------------------------------------------------------------------
static bool writeReg(uint8_t reg, uint8_t val) {
    Wire.beginTransmission(ADDR_MAG);
    Wire.write(reg);
    Wire.write(val);
    return Wire.endTransmission() == 0;
}

static bool readRegs(uint8_t reg, uint8_t* buf, uint8_t n) {
    // LIS3MDL : pour multi-byte read on positionne le bit MSB du registre
    Wire.beginTransmission(ADDR_MAG);
    Wire.write(reg | 0x80);
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom((int)ADDR_MAG, (int)n) != n) return false;
    for (uint8_t i = 0; i < n; i++) buf[i] = Wire.read();
    return true;
}

static int16_t toInt16(uint8_t lo, uint8_t hi) {
    return (int16_t)((uint16_t)hi << 8 | lo);
}

// ----------------------------------------------------------------------------
//   API
// ----------------------------------------------------------------------------
bool magInit() {
    uint8_t id;
    if (!readRegs(LIS3_WHO_AM_I, &id, 1) || id != LIS3_WHO_AM_I_VAL) {
        return false;
    }
    if (!writeReg(LIS3_CTRL_REG1, 0x70)) return false;  // X/Y UHP, 10 Hz
    if (!writeReg(LIS3_CTRL_REG2, 0x00)) return false;  // ±4 gauss
    if (!writeReg(LIS3_CTRL_REG3, 0x00)) return false;  // continuous
    if (!writeReg(LIS3_CTRL_REG4, 0x0C)) return false;  // Z UHP
    return true;
}

bool magReadRaw(int16_t &mx, int16_t &my, int16_t &mz) {
    uint8_t buf[6];
    if (!readRegs(LIS3_OUT_X_L, buf, 6)) return false;
    mx = toInt16(buf[0], buf[1]);
    my = toInt16(buf[2], buf[3]);
    mz = toInt16(buf[4], buf[5]);
    return true;
}

bool magReadCalibrated(float &mx, float &my, float &mz) {
    int16_t rx, ry, rz;
    if (!magReadRaw(rx, ry, rz)) return false;
    mx = (rx * kMagLSBuT - s_ox) * s_sx;
    my = (ry * kMagLSBuT - s_oy) * s_sy;
    mz = (rz * kMagLSBuT - s_oz) * s_sz;
    return true;
}

float magGetHeading() {
    float mx, my, mz;
    if (!magReadCalibrated(mx, my, mz)) return 0.0f;

    // Cap horizontal sans compensation d'inclinaison.
    float h = atan2f(my, mx) * 180.0f / PI;
    if (h < 0.0f) h += 360.0f;
    return h;
}

void magCalibrate(uint16_t durationMs) {
    // L'utilisateur ou la commande appelante doit faire tourner le robot
    // sur 360° pendant durationMs. Pendant ce temps on enregistre min/max.
    float min_x =  1e9f, min_y =  1e9f, min_z =  1e9f;
    float max_x = -1e9f, max_y = -1e9f, max_z = -1e9f;

    const uint32_t start = millis();
    while (millis() - start < durationMs) {
        int16_t rx, ry, rz;
        if (magReadRaw(rx, ry, rz)) {
            const float xu = rx * kMagLSBuT;
            const float yu = ry * kMagLSBuT;
            const float zu = rz * kMagLSBuT;
            if (xu < min_x) min_x = xu;
            if (xu > max_x) max_x = xu;
            if (yu < min_y) min_y = yu;
            if (yu > max_y) max_y = yu;
            if (zu < min_z) min_z = zu;
            if (zu > max_z) max_z = zu;
        }
        delay(20);   // ~50 Hz
    }

    s_ox = (min_x + max_x) * 0.5f;
    s_oy = (min_y + max_y) * 0.5f;
    s_oz = (min_z + max_z) * 0.5f;

    // Égalisation soft-iron simplifiée : amplitude moyenne des trois axes
    const float ax = (max_x - min_x) * 0.5f;
    const float ay = (max_y - min_y) * 0.5f;
    const float az = (max_z - min_z) * 0.5f;
    const float aMean = (ax + ay + az) / 3.0f;
    s_sx = (ax > 1e-3f) ? aMean / ax : 1.0f;
    s_sy = (ay > 1e-3f) ? aMean / ay : 1.0f;
    s_sz = (az > 1e-3f) ? aMean / az : 1.0f;
}

void magSetOffsets(float ox, float oy, float oz) { s_ox = ox; s_oy = oy; s_oz = oz; }
void magSetScales (float sx, float sy, float sz) { s_sx = sx; s_sy = sy; s_sz = sz; }
void magGetOffsets(float &ox, float &oy, float &oz) { ox = s_ox; oy = s_oy; oz = s_oz; }
void magGetScales (float &sx, float &sy, float &sz) { sx = s_sx; sy = s_sy; sz = s_sz; }
