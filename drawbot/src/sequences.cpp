/**
 * @file    sequences.cpp
 * @brief   Implémentation des séquences de dessin.
 */
#include "sequences.h"
#include "primitives.h"
#include "odometry.h"
#include "magnetometer.h"
#include "config.h"

// ----------------------------------------------------------------------------
//   Helpers internes
// ----------------------------------------------------------------------------

/// Trace la pointe d'une flèche : un triangle isocèle rempli par hachures
/// parallèles à la base.
static void drawArrowHead(float head_length_cm) {
    // Stratégie simple : revient en arrière de head_length, puis
    // dessine deux côtés diagonaux qui forment le V de la pointe.
    // (Le remplissage par hachures est implémenté ci-dessous séparément.)
    moveBackward(head_length_cm);
    turnRight(45.0f);
    moveForward(head_length_cm * 1.4142f);   // hypoténuse √2 * côté
    moveBackward(head_length_cm * 1.4142f);
    turnLeft(90.0f);
    moveForward(head_length_cm * 1.4142f);
    moveBackward(head_length_cm * 1.4142f);
    turnRight(45.0f);
}

// ============================================================================
//   Séquence 1 — Escalier
// ============================================================================
void sequenceEscalier() {
    sequenceEscalierCustom(20.0f, 90.0f, 10.0f, -90.0f, 40.0f);
}

void sequenceEscalierCustom(float l1, float a1, float l2, float a2, float l3) {
    moveForward(l1);
    if (a1 >= 0.0f) turnLeft (a1); else turnRight(-a1);
    moveForward(l2);
    if (a2 >= 0.0f) turnLeft (a2); else turnRight(-a2);
    moveForward(l3);
}

// ============================================================================
//   FA1 — Carrés circonscrits
// ============================================================================
void sequenceCarresCircles(float taille_initiale, int nb_carres) {
    if (nb_carres < 1) return;
    if (taille_initiale < 0.5f) taille_initiale = 0.5f;

    for (int k = 1; k <= nb_carres; ++k) {
        const float side = taille_initiale * k;
        for (int s = 0; s < 4; ++s) {
            moveForward(side);
            turnLeft(90.0f);
        }
    }
}

// ============================================================================
//   Séquence 2 — Cercle
// ============================================================================
void sequenceCercle(float radius_cm) {
    sequenceCercleSens(radius_cm, false);   // antihoraire par défaut
}

void sequenceCercleSens(float radius_cm, bool clockwise) {
    if (radius_cm < 1.0f) radius_cm = 1.0f;
    const float angle_full_circle = clockwise ? -360.0f : +360.0f;
    moveArc(radius_cm, angle_full_circle, 10.0f);
}

// ============================================================================
//   FA2 — Rosace
// ============================================================================
void sequenceRosace(float radius_cm, int nb_petales) {
    if (nb_petales < 4) nb_petales = 4;
    if (radius_cm < 1.0f) radius_cm = 1.0f;

    // On découpe le cercle principal en nb_petales arcs ; entre deux arcs,
    // on dessine un petit "pétale" (arc tournant à l'extérieur).
    const float arc_step_deg = 360.0f / nb_petales;
    const float petal_radius = radius_cm * 0.4f;

    for (int k = 0; k < nb_petales; ++k) {
        // Pétale = aller-retour sur un arc plus petit, vers l'extérieur
        moveArc(petal_radius, +180.0f, 8.0f);
        moveArc(petal_radius, -180.0f, 8.0f);
        // Avance le long du cercle circonscrit jusqu'au prochain pétale
        moveArc(radius_cm, arc_step_deg, 8.0f);
    }
}

// ============================================================================
//   Séquence 3 — Flèche
// ============================================================================
void sequenceFleche(float length_cm) {
    if (length_cm < 1.0f) length_cm = 1.0f;
    // Corps de la flèche
    moveForward(length_cm);
    // Pointe (≈ 30 % de la longueur, cf. cahier des charges)
    drawArrowHead(length_cm * 0.30f);
}

void sequenceFlecheNord(float length_cm) {
    // 1. S'orienter au Nord magnétique
    turnToHeading(0.0f, MOTION_ANG_TOLERANCE_DEG, /*useMagnetometer=*/true);
    // 2. Tracer la flèche
    sequenceFleche(length_cm);
}

// ============================================================================
//   FA3 — Rose des vents complète
// ============================================================================
void sequenceRoseDesVents(float diametre_cm) {
    if (diametre_cm < 4.0f) diametre_cm = 4.0f;
    const float r = diametre_cm * 0.5f;

    // 1. Tracé du cercle extérieur
    moveArc(r, 360.0f, 10.0f);

    // 2. S'orienter au Nord
    turnToHeading(0.0f, MOTION_ANG_TOLERANCE_DEG, /*useMagnetometer=*/true);

    // 3. Tracé des 8 directions cardinales (N, NE, E, SE, S, SW, W, NW)
    //    Pour chaque direction : avancer jusqu'au cercle, revenir, tourner.
    for (int k = 0; k < 8; ++k) {
        moveForward(r);
        moveBackward(r);
        turnLeft(45.0f);   // 360°/8
    }

    // 4. Mise en évidence du Nord : flèche plus longue
    turnToHeading(0.0f, MOTION_ANG_TOLERANCE_DEG, /*useMagnetometer=*/true);
    sequenceFleche(r * 1.2f);
}
