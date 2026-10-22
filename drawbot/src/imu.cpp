/**
 * @file    imu.cpp
 * @brief   Implémentation du driver LSM6DS3 (registres I²C).
 */
#include "imu.h"
#include "pins.h"
#include <Wire.h>

// ----------------------------------------------------------------------------
//   Registres LSM6DS3 (cf. datasheet)
// ----------------------------------------------------------------------------
#define LSM6_WHO_AM_I        0x0F
#define LSM6_CTRL1_XL        0x10   // accéléro
#define LSM6_CTRL2_G         0x11   // gyro
#define LSM6_CTRL3_C         0x12
#define LSM6_OUTX_L_G        0x22   // gyro X low byte (auto-incr ensuite)
#define LSM6_OUTX_L_XL       0x28   // accéléro X low byte

#define LSM6_WHO_AM_I_VAL    0x69

// Sensibilités (cf. datasheet § 4.1 et 4.2)
static const float kAccelLSB =  0.061f * 1e-3f;   // g/LSB  pour ±2 g
static const float kGyroLSB  = 17.50f  * 1e-3f;   // dps/LSB pour ±500 dps

// Offsets de gyroscope mesurés lors de la calibration
static float s_gxOffset = 0.0f;
static float s_gyOffset = 0.0f;
static float s_gzOffset = 0.0f;

// ----------------------------------------------------------------------------
//   Helpers I²C
// ----------------------------------------------------------------------------
static bool writeReg(uint8_t reg, uint8_t val) {
    Wire.beginTransmission(ADDR_IMU);
    Wire.write(reg);
    Wire.write(val);
    return Wire.endTransmission() == 0;
}

static bool readRegs(uint8_t reg, uint8_t* buf, uint8_t n) {
    Wire.beginTransmission(ADDR_IMU);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom((int)ADDR_IMU, (int)n) != n) return false;
    for (uint8_t i = 0; i < n; i++) buf[i] = Wire.read();
    return true;
}

static int16_t toInt16(uint8_t lo, uint8_t hi) {
    return (int16_t)((uint16_t)hi << 8 | lo);
}

// ----------------------------------------------------------------------------
//   API
// ----------------------------------------------------------------------------
bool imuInit() {
    uint8_t id;
    if (!readRegs(LSM6_WHO_AM_I, &id, 1) || id != LSM6_WHO_AM_I_VAL) {
        return false;
    }
    // Accéléromètre : 104 Hz, ±2 g
    if (!writeReg(LSM6_CTRL1_XL, 0x40)) return false;
    // Gyroscope     : 104 Hz, ±500 dps
    if (!writeReg(LSM6_CTRL2_G,  0x44)) return false;
    // Auto-increment activé (bit IF_INC = 1)
    if (!writeReg(LSM6_CTRL3_C,  0x44)) return false;
    return true;
}

bool imuReadAccel(float &ax, float &ay, float &az) {
    uint8_t buf[6];
    if (!readRegs(LSM6_OUTX_L_XL, buf, 6)) return false;
    ax = toInt16(buf[0], buf[1]) * kAccelLSB;
    ay = toInt16(buf[2], buf[3]) * kAccelLSB;
    az = toInt16(buf[4], buf[5]) * kAccelLSB;
    return true;
}

bool imuReadGyro(float &gx, float &gy, float &gz) {
    uint8_t buf[6];
    if (!readRegs(LSM6_OUTX_L_G, buf, 6)) return false;
    gx = toInt16(buf[0], buf[1]) * kGyroLSB - s_gxOffset;
    gy = toInt16(buf[2], buf[3]) * kGyroLSB - s_gyOffset;
    gz = toInt16(buf[4], buf[5]) * kGyroLSB - s_gzOffset;
    return true;
}

bool imuReadAll(float* accel, float* gyro) {
    // Lecture en une seule rafale de 12 octets : gyro puis accéléro
    uint8_t buf[12];
    if (!readRegs(LSM6_OUTX_L_G, buf, 12)) return false;
    gyro[0]  = toInt16(buf[0],  buf[1])  * kGyroLSB - s_gxOffset;
    gyro[1]  = toInt16(buf[2],  buf[3])  * kGyroLSB - s_gyOffset;
    gyro[2]  = toInt16(buf[4],  buf[5])  * kGyroLSB - s_gzOffset;
    accel[0] = toInt16(buf[6],  buf[7])  * kAccelLSB;
    accel[1] = toInt16(buf[8],  buf[9])  * kAccelLSB;
    accel[2] = toInt16(buf[10], buf[11]) * kAccelLSB;
    return true;
}

void imuCalibrateGyro() {
    const int N = 500;
    double sx = 0.0, sy = 0.0, sz = 0.0;
    int valid = 0;

    // Reset des offsets pour ne pas biaiser la moyenne
    s_gxOffset = s_gyOffset = s_gzOffset = 0.0f;

    for (int i = 0; i < N; ++i) {
        float gx, gy, gz;
        if (imuReadGyro(gx, gy, gz)) {
            sx += gx; sy += gy; sz += gz;
            ++valid;
        }
        delay(10);   // 100 Hz d'échantillonnage
    }
    if (valid > 0) {
        s_gxOffset = sx / valid;
        s_gyOffset = sy / valid;
        s_gzOffset = sz / valid;
    }
}

void imuGetGyroOffsets(float &ox, float &oy, float &oz) {
    ox = s_gxOffset; oy = s_gyOffset; oz = s_gzOffset;
}
