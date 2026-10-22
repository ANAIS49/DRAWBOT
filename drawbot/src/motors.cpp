/**
 * @file    motors.cpp
 * @brief   Implémentation du driver moteurs.
 *
 * On utilise l'API LEDC d'Espressif (esp32-hal-ledc.h) pour générer un
 * PWM hardware à 20 kHz, 10 bits de résolution, sur 4 canaux dédiés.
 */
#include "motors.h"
#include "pins.h"
#include "config.h"

// Instances globales : les deux moteurs du robot.
Motor motorLeft (IN_1_G, IN_2_G, EN_G,
                 MOTOR_LEDC_CH_IN1_G, MOTOR_LEDC_CH_IN2_G,
                 MOTOR_LEFT_INVERT);

Motor motorRight(IN_1_D, IN_2_D, EN_D,
                 MOTOR_LEDC_CH_IN1_D, MOTOR_LEDC_CH_IN2_D,
                 MOTOR_RIGHT_INVERT);

// ----------------------------------------------------------------------------
//   Implémentation de la classe Motor
// ----------------------------------------------------------------------------
Motor::Motor(int pin_in1, int pin_in2, int pin_en,
             int ch_in1, int ch_in2, bool invert)
    : _pin_in1(pin_in1), _pin_in2(pin_in2), _pin_en(pin_en),
      _ch_in1(ch_in1),   _ch_in2(ch_in2),
      _invert(invert),   _enabled(false) {}

void Motor::begin() {
    pinMode(_pin_en, OUTPUT);
    digitalWrite(_pin_en, LOW);

    // Attache les broches IN1/IN2 au PWM hardware.
    ledcSetup(_ch_in1, MOTOR_PWM_FREQ_HZ, MOTOR_PWM_RESOLUTION);
    ledcSetup(_ch_in2, MOTOR_PWM_FREQ_HZ, MOTOR_PWM_RESOLUTION);
    ledcAttachPin(_pin_in1, _ch_in1);
    ledcAttachPin(_pin_in2, _ch_in2);
    ledcWrite(_ch_in1, 0);
    ledcWrite(_ch_in2, 0);

    enable(true);
}

void Motor::setSpeed(int speed) {
    // Borne la commande dans [-MAX, +MAX]
    if (speed >  MOTOR_PWM_MAX) speed =  MOTOR_PWM_MAX;
    if (speed < -MOTOR_PWM_MAX) speed = -MOTOR_PWM_MAX;
    if (_invert) speed = -speed;

    if (speed > 0) {
        ledcWrite(_ch_in1, speed);
        ledcWrite(_ch_in2, 0);
    } else if (speed < 0) {
        ledcWrite(_ch_in1, 0);
        ledcWrite(_ch_in2, -speed);
    } else {
        // Vitesse nulle : roue libre (au lieu d'un freinage permanent)
        ledcWrite(_ch_in1, 0);
        ledcWrite(_ch_in2, 0);
    }
}

void Motor::brake() {
    // Freinage actif : IN1=IN2=HIGH (PWM = max sur les deux canaux)
    ledcWrite(_ch_in1, MOTOR_PWM_MAX);
    ledcWrite(_ch_in2, MOTOR_PWM_MAX);
}

void Motor::coast() {
    ledcWrite(_ch_in1, 0);
    ledcWrite(_ch_in2, 0);
}

void Motor::enable(bool on) {
    _enabled = on;
    digitalWrite(_pin_en, on ? HIGH : LOW);
}

// ----------------------------------------------------------------------------
//   Fonctions globales
// ----------------------------------------------------------------------------
void motorsInit() {
    motorLeft.begin();
    motorRight.begin();
}

void motorsStop() {
    motorLeft.brake();
    motorRight.brake();
}

void motorsSetSpeeds(int left, int right) {
    motorLeft.setSpeed(left);
    motorRight.setSpeed(right);
}
