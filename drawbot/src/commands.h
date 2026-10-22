/**
 * @file    commands.h
 * @brief   Parser de commandes textuelles reçues sur le port série.
 *
 * Format : COMMANDE param1 param2 ... \n
 *
 * Réponses préfixées :
 *   [OK]   succès
 *   [ERR]  erreur
 *   [DATA] données capteurs
 *   [INFO] message informatif
 *   [LOG]  log debug
 */
#pragma once

void commandsInit();

/// À appeler dans loop() ; lit les caractères entrants et exécute les
/// commandes complètes reçues.
void commandsProcess();

/// Émet la télémétrie au format Teleplot (>nom:val).
void sendTelemetry();
