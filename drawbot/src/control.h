/**
 * @file    control.h
 * @brief   Asservissement en cascade : vitesse roues (bas niveau) +
 *          pose distance/cap (haut niveau).
 *
 * Architecture :
 *
 *      consigne (v, ω)               PID distance/cap
 *           │                              ▲
 *           ▼                              │  pose actuelle
 *      [ v_left, v_right ]                 │
 *           │                              │
 *           ▼                              │
 *      PID vitesse  ────► PWM moteur  ───► encodeurs ──► odométrie
 *
 *  - Boucle vitesse roues : 100 Hz
 *  - Boucle haut niveau   :  50 Hz
 */
#pragma once

#include <Arduino.h>

void controlInit();

/// À appeler dans loop() ; gère les deux niveaux d'asservissement.
void controlUpdate();

// ---------------------------------------------------------------------------
//   Niveau bas : consignes de vitesse roues directes (cm/s, signées)
// ---------------------------------------------------------------------------
void  setWheelSpeeds(float v_left_cms, float v_right_cms);

// ---------------------------------------------------------------------------
//   Niveau haut : consignes (v, ω) ; le module convertit vers les roues.
// ---------------------------------------------------------------------------
void  setLinearAngular(float v_cms, float omega_dps);

// ---------------------------------------------------------------------------
//   Mode "pose target" : viser un point (distance, cap)
// ---------------------------------------------------------------------------
/**
 * @brief Démarre un asservissement haut niveau qui amène le robot à
 *        une pose cible (distance signée à parcourir + cap à maintenir).
 *
 * @param target_distance_cm  distance à parcourir, signée
 * @param target_heading_deg  cap absolu visé (utilise odometryGetTheta)
 * @param max_speed_cms       vitesse linéaire max
 */
void setPoseTarget(float target_distance_cm,
                   float target_heading_deg,
                   float max_speed_cms);

/// Arrête l'asservissement haut niveau et coupe les roues.
void controlAbort();

/// true si une primitive (pose target) est encore en cours.
bool controlIsBusy();

// ---------------------------------------------------------------------------
//   PID accessibles depuis l'extérieur (pour les commandes SETPID_*)
// ---------------------------------------------------------------------------
void setSpeedPIDGains   (float kp, float ki, float kd);
void setDistancePIDGains(float kp, float ki, float kd);
void setHeadingPIDGains (float kp, float ki, float kd);

void getSpeedPIDGains   (float &kp, float &ki, float &kd);
void getDistancePIDGains(float &kp, float &ki, float &kd);
void getHeadingPIDGains (float &kp, float &ki, float &kd);
