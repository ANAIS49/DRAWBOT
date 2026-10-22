/**
 * @file    motors.h
 * @brief   Pilotage des deux moteurs DRV8837 en PWM hardware (LEDC).
 *
 * Le DRV8837 utilise le couple (IN1, IN2) :
 *   - IN1=PWM, IN2=LOW → marche avant proportionnelle
 *   - IN1=LOW, IN2=PWM → marche arrière proportionnelle
 *   - IN1=IN2=LOW      → roue libre
 *   - IN1=IN2=HIGH     → freinage actif
 * EN doit être HIGH pour activer le pont.
 */
#pragma once

#include <Arduino.h>

/**
 * @class Motor
 * @brief Pilote un moteur DRV8837 via deux canaux LEDC.
 */
class Motor {
public:
    /**
     * @brief Construit un objet moteur (pas d'init matériel ici).
     * @param pin_in1   GPIO IN1
     * @param pin_in2   GPIO IN2
     * @param pin_en    GPIO Enable (sleep) — HIGH pour activer
     * @param ch_in1    Canal LEDC pour IN1
     * @param ch_in2    Canal LEDC pour IN2
     * @param invert    Inverser le sens (câblage variable selon les robots)
     */
    Motor(int pin_in1, int pin_in2, int pin_en,
          int ch_in1, int ch_in2, bool invert);

    /// Configure les pins et les canaux LEDC. À appeler une fois dans setup().
    void begin();

    /**
     * @brief  Applique une commande de vitesse signée.
     * @param  speed valeur dans [-1023, +1023]. Positif = avant.
     */
    void setSpeed(int speed);

    /// Freinage actif (IN1=IN2=HIGH).
    void brake();

    /// Roue libre (IN1=IN2=LOW).
    void coast();

    /// Active ou désactive le driver via la broche EN.
    void enable(bool on);

private:
    int  _pin_in1, _pin_in2, _pin_en;
    int  _ch_in1,  _ch_in2;
    bool _invert;
    bool _enabled;
};

extern Motor motorLeft;
extern Motor motorRight;

/**
 * @brief Initialise les deux moteurs (à appeler dans setup()).
 */
void motorsInit();

/**
 * @brief Arrête immédiatement les deux moteurs (freinage actif).
 */
void motorsStop();

/**
 * @brief Applique des commandes PWM signées sur les deux moteurs.
 * @param left   commande gauche (-1023..+1023)
 * @param right  commande droite (-1023..+1023)
 */
void motorsSetSpeeds(int left, int right);
