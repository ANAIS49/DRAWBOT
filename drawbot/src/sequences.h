/**
 * @file    sequences.h
 * @brief   Séquences de dessin du Drawbot (escalier, cercle, rose des
 *          vents) ainsi que les fonctionnalités avancées (FA1/2/3).
 */
#pragma once

#include <Arduino.h>

// ============================================================================
//   Séquence 1 — Escalier (5 segments)
// ============================================================================
void sequenceEscalier();

/**
 * @brief Variante paramétrable de l'escalier.
 * @param l1  longueur 1er segment (cm)
 * @param a1  angle 1 (°, positif = gauche)
 * @param l2  longueur 2e segment (cm)
 * @param a2  angle 2 (°, positif = gauche)
 * @param l3  longueur 3e segment (cm)
 */
void sequenceEscalierCustom(float l1, float a1, float l2, float a2, float l3);

/**
 * @brief FA1 — suite de carrés circonscrits.
 * @param taille_initiale  longueur du côté du premier carré (cm)
 * @param nb_carres        nombre de carrés à dessiner
 *
 * Chaque carré k (k = 1..nb_carres) est de côté k × taille_initiale ;
 * tous partagent un sommet commun (l'origine) — d'où "circonscrits".
 */
void sequenceCarresCircles(float taille_initiale, int nb_carres);

// ============================================================================
//   Séquence 2 — Cercle
// ============================================================================
void sequenceCercle(float radius_cm);
void sequenceCercleSens(float radius_cm, bool clockwise);

/**
 * @brief FA2 — rosace circonscrite à un cercle de rayon donné.
 * @param radius_cm   rayon du cercle circonscrit
 * @param nb_petales  nombre de pétales (≥ 4 selon cahier des charges)
 */
void sequenceRosace(float radius_cm, int nb_petales);

// ============================================================================
//   Séquence 3 — Flèche / rose des vents
// ============================================================================
/// Trace une flèche orientée vers l'angle courant du robot.
void sequenceFleche(float length_cm);

/// S'oriente vers le Nord magnétique puis trace la flèche.
void sequenceFlecheNord(float length_cm);

/// FA3 — Rose des vents complète (cercle + 8 directions cardinales).
void sequenceRoseDesVents(float diametre_cm);
