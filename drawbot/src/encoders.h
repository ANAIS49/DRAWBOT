/**
 * @file    encoders.h
 * @brief   Lecture des deux encodeurs à effet Hall en quadrature.
 *
 * Le décodage se fait en mode 1× (interruption uniquement sur les fronts
 * montants de la voie A) ; on lit ensuite la voie B pour déterminer le
 * sens. Suffisant pour notre besoin (vitesse modérée + ~700 tics/tour).
 */
#pragma once

#include <Arduino.h>

/// Initialise les broches d'encodeurs et attache les ISR.
void encodersInit();

/// Compteur cumulé d'impulsions, voie A roue gauche.
int32_t encoderLeftCount();

/// Compteur cumulé d'impulsions, voie A roue droite.
int32_t encoderRightCount();

/// Remet à zéro les deux compteurs (atomique).
void encoderResetCounts();

/// Distance parcourue par la roue gauche depuis le dernier reset, en cm.
float encoderLeftDistanceCm();

/// Distance parcourue par la roue droite depuis le dernier reset, en cm.
float encoderRightDistanceCm();

/// Vitesse instantanée (filtrée) de la roue gauche, en cm/s, signée.
float encoderLeftSpeedCmPerSec();

/// Vitesse instantanée (filtrée) de la roue droite, en cm/s, signée.
float encoderRightSpeedCmPerSec();

/**
 * @brief Met à jour les vitesses filtrées (à appeler périodiquement,
 *        idéalement à 20 Hz, depuis la boucle principale).
 *
 * Le calcul est basé sur l'évolution des compteurs depuis l'appel précédent
 * ; on applique ensuite un filtre passe-bas exponentiel pour lisser.
 */
void encoderUpdateSpeeds();

/**
 * @brief Détecte un blocage mécanique : PWM appliqué mais aucun tic.
 * @param  pwm_left  PWM gauche actuel (-1023..+1023)
 * @param  pwm_right PWM droit  actuel (-1023..+1023)
 * @return true si un blocage est détecté depuis STALL_DETECT_DURATION_MS.
 */
bool encoderDetectStall(int pwm_left, int pwm_right);
