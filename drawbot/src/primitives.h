/**
 * @file    primitives.h
 * @brief   Mouvements de base bloquants et asynchrones servant de briques
 *          aux séquences (escalier, cercle, rose des vents).
 *
 * Critères d'arrêt :
 *   - erreur de position < MOTION_POS_TOLERANCE_CM
 *   - vitesse < MOTION_SPEED_TOLERANCE pendant MOTION_STABLE_DURATION_MS
 *   - timeout MOTION_TIMEOUT_MS
 */
#pragma once

#include <Arduino.h>
#include "config.h"

// ============================================================================
//   Mouvements bloquants (renvoient quand le robot est arrêté à la cible)
// ============================================================================
bool moveForward (float distance_cm, float speed_cm_s = 10.0f);
bool moveBackward(float distance_cm, float speed_cm_s = 10.0f);

bool turnLeft (float angle_deg, float speed_deg_s = 60.0f);
bool turnRight(float angle_deg, float speed_deg_s = 60.0f);

/// Tourne vers un cap absolu (utilise odométrie ou magnétomètre selon flag).
bool turnToHeading(float target_deg, float tolerance_deg = MOTION_ANG_TOLERANCE_DEG,
                   bool useMagnetometer = false);

/**
 * @brief Trace un arc de cercle.
 * @param radius_cm   rayon (positif). Le sens dépend du signe d'angle_deg.
 * @param angle_deg   angle d'arc (signé : positif = horaire vu de dessus,
 *                    selon convention robot).
 * @param speed_cm_s  vitesse linéaire de la roue extérieure
 */
bool moveArc(float radius_cm, float angle_deg, float speed_cm_s = 10.0f);

// ============================================================================
//   Mouvements asynchrones (à compléter avec moveForwardAsync etc.)
// ============================================================================
void moveForwardAsync(float distance_cm, float speed_cm_s);

/// true si la dernière primitive asynchrone est terminée.
bool isMotionComplete();

/// Stoppe la primitive en cours (avec ou sans freinage actif).
void stopMotion(bool brake = true);
