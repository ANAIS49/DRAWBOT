/**
 * @file    config.h
 * @brief   Constantes de configuration du Drawbot (dimensions, gains PID,
 *          inversions, fréquences d'asservissement).
 *
 * Toute valeur susceptible d'être recalibrée pour un robot physique
 * particulier doit être placée ici (et non dispersée dans les modules).
 */
#pragma once

#include <Arduino.h>

// ============================================================================
//   Identification
// ============================================================================
#define FIRMWARE_VERSION   "1.0.0"

// ============================================================================
//   Dimensions mécaniques  (TODO: à calibrer précisément sur le robot réel)
// ============================================================================
#define WHEEL_DIAMETER_MM       90.0f    ///< Diamètre des roues
#define WHEEL_BASE_MM          120.0f    ///< Entraxe entre les deux roues
#define WHEEL_CIRCUMFERENCE_MM  (PI * WHEEL_DIAMETER_MM)

#define WHEEL_DIAMETER_CM       (WHEEL_DIAMETER_MM / 10.0f)
#define WHEEL_BASE_CM           (WHEEL_BASE_MM / 10.0f)
#define WHEEL_CIRCUMFERENCE_CM  (WHEEL_CIRCUMFERENCE_MM / 10.0f)

// ============================================================================
//   Encodeurs    (TODO: 7 tics/tour moteur × ratio réducteur — à mesurer)
// ============================================================================
#define ENCODER_TICS_PER_REV    700      ///< Tics par tour de roue
#define ENCODER_INVERT_LEFT     false
#define ENCODER_INVERT_RIGHT    false

// ============================================================================
//   Moteurs : sens et limites
// ============================================================================
#define MOTOR_LEFT_INVERT       false    ///< Inverser si la roue G part en arrière
#define MOTOR_RIGHT_INVERT      false    ///< Idem pour la roue D
#define MOTOR_PWM_FREQ_HZ       20000    ///< 20 kHz : silencieux et réactif
#define MOTOR_PWM_RESOLUTION    10       ///< 10 bits → 0..1023
#define MOTOR_PWM_MAX           1023

// Canaux LEDC (0 à 15 sur ESP32)
#define MOTOR_LEDC_CH_IN1_G     0
#define MOTOR_LEDC_CH_IN2_G     1
#define MOTOR_LEDC_CH_IN1_D     2
#define MOTOR_LEDC_CH_IN2_D     3

// ============================================================================
//   Cinématique
// ============================================================================
#define MAX_LINEAR_SPEED_CM_S   25.0f    ///< Vitesse max théorique du robot
#define MAX_ANGULAR_SPEED_DPS  120.0f    ///< Vitesse de rotation max

// ============================================================================
//   Fréquences des boucles (en ms entre 2 itérations)
// ============================================================================
#define CONTROL_PERIOD_MS       10       ///< 100 Hz : boucle vitesse roues
#define ODOMETRY_PERIOD_MS      20       ///< 50 Hz  : intégration de pose
#define TELEMETRY_PERIOD_MS    100       ///< 10 Hz  : envoi Teleplot
#define ENCODER_SPEED_WINDOW_MS 50       ///< Fenêtre de calcul de vitesse

// ============================================================================
//   Gains PID initiaux  (TODO: à affiner après TEST_PWM_SWEEP)
// ============================================================================
#define PID_SPEED_KP            15.0f
#define PID_SPEED_KI            80.0f
#define PID_SPEED_KD             0.0f

#define PID_DISTANCE_KP          8.0f
#define PID_DISTANCE_KI          0.5f
#define PID_DISTANCE_KD          0.2f

#define PID_HEADING_KP           4.0f
#define PID_HEADING_KI           0.1f
#define PID_HEADING_KD           0.5f

// Filtre complémentaire odométrie / gyro
#define ODOMETRY_GYRO_ALPHA      0.98f   ///< Plus haut = plus de gyro

// ============================================================================
//   Critères d'arrêt des primitives
// ============================================================================
#define MOTION_POS_TOLERANCE_CM    0.5f
#define MOTION_ANG_TOLERANCE_DEG   2.0f
#define MOTION_SPEED_TOLERANCE     1.0f   ///< cm/s en dessous → "à l'arrêt"
#define MOTION_STABLE_DURATION_MS  100
#define MOTION_TIMEOUT_MS         10000

// ============================================================================
//   Sécurité / watchdog
// ============================================================================
#define STALL_DETECT_DURATION_MS  500     ///< PWM > 0 mais pas de tics → bloqué
#define BATTERY_LOW_VOLTAGE       4.0f    ///< 4 piles AA : seuil critique

// ============================================================================
//   Série
// ============================================================================
#define SERIAL_BAUD_RATE          115200
