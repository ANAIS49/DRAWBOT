/**
 * @file    pid.cpp
 * @brief   Implémentation du régulateur PID générique.
 */
#include "pid.h"
#include <Arduino.h>

PID::PID(float kp, float ki, float kd)
    : _kp(kp), _ki(ki), _kd(kd),
      _setpoint(0.0f),
      _integral(0.0f),
      _last_measurement(0.0f),
      _last_deriv_filtered(0.0f),
      _out_min(-1e9f), _out_max(1e9f),
      _i_min(-1e9f),   _i_max(1e9f),
      _d_alpha(0.1f),
      _has_last(false) {}

void PID::setGains(float kp, float ki, float kd) {
    _kp = kp; _ki = ki; _kd = kd;
}

void PID::getGains(float &kp, float &ki, float &kd) const {
    kp = _kp; ki = _ki; kd = _kd;
}

void PID::setOutputLimits(float minOut, float maxOut) {
    _out_min = minOut;
    _out_max = maxOut;
}

void PID::setIntegralLimits(float minI, float maxI) {
    _i_min = minI;
    _i_max = maxI;
}

void PID::setDerivativeFilter(float alpha) {
    if (alpha < 0.0f) alpha = 0.0f;
    if (alpha > 1.0f) alpha = 1.0f;
    _d_alpha = alpha;
}

void PID::setSetpoint(float sp) {
    _setpoint = sp;
}

float PID::compute(float measurement, float dt) {
    if (dt <= 0.0f) dt = 1e-3f;

    const float error = _setpoint - measurement;

    // --- Terme intégral avec clamp anti-windup ---
    _integral += error * dt * _ki;
    if (_integral > _i_max) _integral = _i_max;
    if (_integral < _i_min) _integral = _i_min;

    // --- Terme dérivé sur la mesure (signe inversé) ---
    float deriv = 0.0f;
    if (_has_last) {
        const float raw = -(measurement - _last_measurement) / dt;
        deriv = _d_alpha * raw + (1.0f - _d_alpha) * _last_deriv_filtered;
    }
    _last_deriv_filtered = deriv;
    _last_measurement = measurement;
    _has_last = true;

    // --- Sortie totale ---
    float out = _kp * error + _integral + _kd * deriv;

    // Saturation
    if (out > _out_max) out = _out_max;
    if (out < _out_min) out = _out_min;
    return out;
}

void PID::reset() {
    _integral = 0.0f;
    _last_measurement = 0.0f;
    _last_deriv_filtered = 0.0f;
    _has_last = false;
}
