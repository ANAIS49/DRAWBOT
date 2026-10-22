/**
 * @file    pins.h
 * @brief   Définitions de toutes les broches GPIO du Drawbot.
 *
 * Ce fichier centralise la totalité du pinout matériel : si le câblage
 * change, c'est le seul endroit à modifier. Aucun autre fichier ne doit
 * coder en dur un numéro de broche.
 */
#pragma once

// ============================================================================
//   LEDs utilisateur
// ============================================================================
#define LEDU1            25      ///< LED utilisateur 1 (statut "prêt")
#define LEDU2            26      ///< LED utilisateur 2 (libre)

// ============================================================================
//   Drivers moteurs DRV8837
//   - EN (sleep)  : à mettre HIGH pour activer le driver
//   - IN1 / IN2   : commandes PWM (sens dépendant du couple actif)
// ============================================================================

// Enable
#define EN_D             23      ///< Enable moteur droit
#define EN_G              4      ///< Enable moteur gauche

// Moteur droit
#define IN_1_D           19      ///< IN1 moteur droit (PWM avant)
#define IN_2_D           18      ///< IN2 moteur droit (PWM arrière)

// Moteur gauche
#define IN_1_G           17      ///< IN1 moteur gauche (PWM avant)
#define IN_2_G           16      ///< IN2 moteur gauche (PWM arrière)

// ============================================================================
//   Encodeurs à effet Hall (quadrature, 2 voies par roue)
// ============================================================================
#define ENC_G_CH_A       32      ///< Encodeur gauche, voie A (interruption)
#define ENC_G_CH_B       33      ///< Encodeur gauche, voie B (sens)

#define ENC_D_CH_A       27      ///< Encodeur droit, voie A (interruption)
#define ENC_D_CH_B       14      ///< Encodeur droit, voie B (sens)

// ============================================================================
//   Bus I²C : IMU LSM6DS3 (0x6B) + magnétomètre LIS3MDL (0x1E)
// ============================================================================
#define SDA_PIN          21
#define SCL_PIN          22

#define ADDR_IMU         0x6B    ///< Adresse I²C du LSM6DS3
#define ADDR_MAG         0x1E    ///< Adresse I²C du LIS3MDL
