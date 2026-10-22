# Drawbot — Firmware ESP32

Firmware embarqué pour le robot **Drawbot** (deux roues motrices, ESP32 + IMU
LSM6DS3 + magnétomètre LIS3MDL + 2 drivers DRV8837).

Ce firmware pilote les moteurs, lit les capteurs en I²C bas niveau, asservit
la vitesse de chaque roue puis la pose (distance + cap), et exécute les
trois séquences de dessin du cahier des charges (escalier, cercle, rose des
vents) ainsi que les fonctionnalités avancées FA1/FA2/FA3.

> Cette première version n'utilise **ni WiFi ni Bluetooth** : toutes les
> commandes passent par le port série à **115 200 bauds**. La GUI Python
> séparée (dans `gui/`) sera plus tard rebranchée par-dessus.

---

## Sommaire

1. [Matériel](#matériel)
2. [Arborescence](#arborescence)
3. [Installation du toolchain](#installation-du-toolchain)
4. [Compilation et flashage](#compilation-et-flashage)
5. [Procédure de calibration au premier démarrage](#procédure-de-calibration-au-premier-démarrage)
6. [Liste des commandes série](#liste-des-commandes-série)
7. [Méthodologie de réglage des PID](#méthodologie-de-réglage-des-pid)
8. [Télémétrie Teleplot](#télémétrie-teleplot)
9. [Sécurité](#sécurité)

---

## Matériel

| Composant            | Détail                                       |
|----------------------|----------------------------------------------|
| Microcontrôleur      | NodeMCU ESP32 (ESP-WROOM-32), 240 MHz, 3,3 V |
| Moteurs              | 2× motoréducteurs N20, 100 RPM @ 6 V         |
| Drivers moteurs      | 2× DRV8837DSGR (PWM via LEDC, 20 kHz, 10 bits) |
| Encodeurs            | Effet Hall en quadrature (~700 tics/tour roue) |
| IMU                  | LSM6DS3, I²C 0x6B, 104 Hz, ±2 g / ±500 dps   |
| Magnétomètre         | LIS3MDL, I²C 0x1E, 10 Hz UHP, ±4 gauss       |
| Roues                | Ø 90 mm, entraxe ≈ 120 mm                    |
| Alimentation         | 4× LR6 (AA)                                  |

Pinout précis : voir [src/pins.h](src/pins.h). Aucun fichier ne doit coder
une broche en dur en dehors de ce header.

## Arborescence

```
Drawbot/
├── platformio.ini             configuration PlatformIO (ESP32, framework=arduino)
├── README.md
├── test.txt                   scénario de validation à coller dans le moniteur série
├── docs/
│   └── calibration.md         checklist de mise en service
├── src/
│   ├── main.cpp               setup() + loop() (≡ drawbot.ino)
│   ├── pins.h                 pinout matériel
│   ├── config.h               constantes (dimensions, gains PID, périodes)
│   ├── motors.h / .cpp        driver moteurs DRV8837 via LEDC
│   ├── encoders.h / .cpp      lecture quadrature + ISR + vitesse filtrée
│   ├── imu.h / .cpp           driver LSM6DS3 (registres I²C bas niveau)
│   ├── magnetometer.h / .cpp  driver LIS3MDL + calibration hard-iron
│   ├── pid.h / .cpp           régulateur PID générique (anti-windup, dérivée filtrée)
│   ├── odometry.h / .cpp      modèle différentiel midpoint + fusion gyro
│   ├── control.h / .cpp       cascade vitesse roues / pose
│   ├── primitives.h / .cpp    moveForward, turnLeft, moveArc, ...
│   ├── sequences.h / .cpp     escalier, cercle, rose, FA1/2/3
│   └── commands.h / .cpp      parser série + télémétrie Teleplot
└── gui/                       (interface Python PyQt5, projet séparé)
```

## Installation du toolchain

### Option A — PlatformIO (recommandée)

1. Installer [PlatformIO](https://platformio.org/install) (extension VS Code
   ou CLI).
2. Ouvrir le dossier du projet : PlatformIO détecte automatiquement
   `platformio.ini` et installe le core ESP32 d'Espressif au premier build.
3. Brancher l'ESP32 en USB, puis :
   ```bash
   pio run                # compile
   pio run -t upload      # flashe
   pio device monitor -b 115200   # ouvre le moniteur série
   ```

### Option B — Arduino IDE 2.x

1. Préférences → "Boards Manager URLs", ajouter :
   `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
2. Outils → Type de carte → `ESP32 Dev Module`
3. Copier tout le contenu de `src/` dans un dossier nommé `drawbot/`,
   renommer `main.cpp` en `drawbot.ino`.
4. Ouvrir `drawbot.ino`, sélectionner le port, **Téléverser**.

## Compilation et flashage

```bash
pio run -e esp32dev -t upload     # PlatformIO CLI
```

À la première mise sous tension, le firmware affiche dans le moniteur série :

```
[INFO] Drawbot firmware v1.0.0 starting...
[OK]  IMU init
[OK]  MAG init
[INFO] Calibrating gyro... keep robot still 5 s
[OK]  Gyro calibrated
[OK]  Drawbot ready. Type HELP for commands.
```

## Procédure de calibration au premier démarrage

Voir aussi la [checklist détaillée](docs/calibration.md).

1. **Mécanique**
   - Mesurer précisément l'entraxe roue à roue → ajuster `WHEEL_BASE_MM`
     dans [src/config.h](src/config.h) (TODO).
   - Mesurer le diamètre des roues → `WHEEL_DIAMETER_MM`.
2. **Encodeurs**
   - Faire une rotation manuelle d'exactement 1 tour de roue, lire les tics
     via `TEST_ENCODERS`. Ajuster `ENCODER_TICS_PER_REV` (TODO).
   - Si les sens des compteurs sont inversés : passer
     `ENCODER_INVERT_LEFT` / `ENCODER_INVERT_RIGHT` à `true`.
3. **Moteurs**
   - Lancer `TEST_MOTORS` : la roue gauche puis droite doivent partir vers
     l'avant. Si l'inverse : `MOTOR_*_INVERT = true`.
4. **Gyroscope**
   - Robot immobile, exécuter `CALIB_GYRO`. Les offsets s'affichent.
5. **Magnétomètre**
   - Loin de toute masse métallique, exécuter `CALIB_MAG` ; le robot tourne
     automatiquement à 36 °/s pendant 10 s pour collecter min/max.
6. **PID vitesse**
   - Lancer `TEST_PWM_SWEEP` pour mesurer la relation PWM ↔ vitesse roue.
   - Ajuster `PID_SPEED_KP/KI/KD` ; valider avec `SETSPEED` et l'odométrie.
7. **PID pose** (distance + cap)
   - Lancer `TEST_SQUARE` (4 côtés × 20 cm + 4 rotations 90°). L'erreur de
     fermeture (X, Y) doit rester sous ~2 cm après réglage.

## Liste des commandes série

Format : `COMMANDE arg1 arg2 ...\n`. Réponses préfixées par `[OK]`, `[ERR]`,
`[DATA]`, `[INFO]`, `[LOG]`.

### Pilotage manuel

| Commande                      | Effet                                  |
|-------------------------------|----------------------------------------|
| `FORWARD <cm>`                | Avance bloquant                        |
| `BACKWARD <cm>`               | Recule bloquant                        |
| `LEFT <deg>`                  | Tourne à gauche                        |
| `RIGHT <deg>`                 | Tourne à droite                        |
| `STOP`                        | Arrêt immédiat (controlAbort)          |
| `SETSPEED <pwmL> <pwmR>`      | PWM direct, -1023..+1023 (test)        |

### Séquences

| Commande                       | Effet                                            |
|--------------------------------|--------------------------------------------------|
| `SEQ1`                         | Escalier par défaut (20 / 90 / 10 / -90 / 40)    |
| `SEQ1 l1 a1 l2 a2 l3`          | Escalier paramétrable                            |
| `SEQ2 <radius>`                | Cercle de rayon donné                            |
| `SEQ3 <length>`                | Flèche orientée Nord magnétique                  |
| `SQUARES <size> <nb>`          | FA1 — carrés circonscrits                        |
| `ROSACE <r> <petals>`          | FA2 — rosace (≥ 4 pétales)                       |
| `COMPASS <diam>`               | FA3 — rose des vents complète                    |

### Capteurs et état

| Commande     | Réponse                                                         |
|--------------|------------------------------------------------------------------|
| `GETPOSE`    | `[DATA] POSE x y theta`                                         |
| `GETIMU`     | `[DATA] IMU ax ay az gx gy gz`                                  |
| `GETMAG`     | `[DATA] MAG mx my mz heading`                                   |
| `GETENC`     | `[DATA] ENC ticsL ticsR speedL speedR`                          |
| `GETBAT`     | `[DATA] BAT volts` (TODO : brancher le pont diviseur sur ADC)   |

### Calibration

| Commande      | Effet                                          |
|---------------|------------------------------------------------|
| `CALIB_GYRO`  | Calibre les offsets du gyroscope (5 s)         |
| `CALIB_MAG`   | Calibre le magnétomètre (rotation 360°, 10 s)  |
| `RESET_POSE`  | Remet pose et compteurs encodeurs à zéro       |

### Réglage PID

| Commande                              | Effet                                     |
|---------------------------------------|-------------------------------------------|
| `SETPID_SPEED <kp> <ki> <kd>`         | Asservissement vitesse roues              |
| `SETPID_DIST <kp> <ki> <kd>`          | PID distance (mode pose target)           |
| `SETPID_HEAD <kp> <ki> <kd>`          | PID cap                                   |
| `GETPID`                              | Affiche les trois jeux de gains           |

### Système

| Commande   | Effet                                |
|------------|--------------------------------------|
| `HELP`     | Liste les commandes                  |
| `PING`     | Répond `PONG`                        |
| `VERSION`  | Affiche la version du firmware       |
| `REBOOT`   | Redémarre l'ESP32                    |

### Tests

| Commande         | Effet                                          |
|------------------|------------------------------------------------|
| `TEST_MOTORS`    | Avance / recule / pivot, 1 s par étape         |
| `TEST_ENCODERS`  | Affiche les tics pendant 5 s                   |
| `TEST_IMU`       | Affiche les valeurs IMU pendant 5 s            |
| `TEST_MAG`       | Affiche le cap magnétique pendant 5 s          |
| `TEST_PWM_SWEEP` | Sweep PWM 0 → 1000 par pas de 50               |
| `TEST_SQUARE`    | Carré 20 cm × 4 (vérif odométrie)              |
| `TEST_TURN_360`  | Rotation 360° (erreur de fermeture cap)        |

## Méthodologie de réglage des PID

L'asservissement est en cascade — on règle **du plus interne au plus externe**.

### 1. Cartographier la dynamique des moteurs

```
TEST_PWM_SWEEP
```

Tracer la vitesse mesurée en fonction du PWM. La courbe doit être à peu
près linéaire au-delà du seuil de démarrage (~150 PWM typiquement).

### 2. PID vitesse roues

- Partir de `kp = 15, ki = 80, kd = 0` (valeurs initiales `config.h`).
- `SETSPEED 600 600` : observer dans Teleplot que `speedL/R` rejoignent
  rapidement la consigne sans dépassement excessif.
- Augmenter `kp` jusqu'aux limites de stabilité, puis ajouter `ki` jusqu'à
  annuler l'erreur statique.

### 3. PID distance

- Avec un PID vitesse stable, lancer `FORWARD 30` plusieurs fois et
  mesurer l'erreur de position.
- Augmenter `kp` distance jusqu'à un dépassement de quelques mm puis
  ajouter `kd` pour amortir.

### 4. PID cap

- Lancer `TEST_TURN_360` et viser une erreur de fermeture < ~3°.
- Si oscillation : réduire `kp`, augmenter `kd`.

## Télémétrie Teleplot

Le firmware émet à 10 Hz les variables suivantes au format Teleplot
(`>nom:val\n`) :

```
>x:12.34
>y:-3.21
>theta:87.5
>speedL:8.20
>speedR:8.05
>heading:248.3
```

L'extension Teleplot (VS Code) ouvre automatiquement les courbes —
indispensable pour le réglage PID.

## Sécurité

- Watchdog de 10 s sur chaque primitive (`MOTION_TIMEOUT_MS`).
- Détection de blocage : si PWM > 100 mais aucun tic encodeur pendant
  500 ms, `controlAbort()` est déclenché.
- Vitesses bornées (`MAX_LINEAR_SPEED_CM_S`, `MAX_ANGULAR_SPEED_DPS`) à
  toutes les couches.
- Anti-windup PID par clamp explicite de l'intégrale.
- Tous les setters bornent leurs paramètres avant utilisation.

## Contraintes respectées

- ✅ Compilable Arduino IDE 2.x / PlatformIO sans warning.
- ✅ Pas de `new`/`delete` dans la boucle, pas de `String` dynamique.
- ✅ Pas de `delay()` long dans les zones critiques (boucles d'asservissement).
- ✅ Toutes les ISR en `IRAM_ATTR`.
- ✅ Code commenté en français, autoportant.
- ✅ Registres I²C bas niveau pour LSM6DS3 et LIS3MDL (aucune lib externe).
- ❌ Pas de WiFi/BT pour cette première version (prévu plus tard).
