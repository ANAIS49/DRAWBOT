# Checklist de calibration — Drawbot

Avant la **première utilisation** sur un robot physique neuf, parcourir
cette liste dans l'ordre. Chaque case porte la référence du fichier ou de
la commande à utiliser.

---

## A. Pré-requis matériels

- [ ] Piles AA neuves (ou pleinement chargées) installées.
- [ ] Roues correctement emboîtées sur les arbres ; pas de jeu axial.
- [ ] Stylo monté à mi-course du servo (au repos = stylo levé).
- [ ] Surface de test plane et homogène (papier blanc A3 minimum).

## B. Vérification du câblage

- [ ] Brocher un multimètre sur EN_G (GPIO 4) et EN_D (GPIO 23) :
      vérifier qu'ils passent à 3,3 V au démarrage.
- [ ] Vérifier la présence de l'IMU et du magnétomètre :
      `pio device monitor`, observer `[OK] IMU init` et `[OK] MAG init`.
      Si `[ERR] IMU init failed` : vérifier I²C (SDA = 21, SCL = 22) et
      l'alimentation 3,3 V de la breakout.

## C. Constantes mécaniques (`src/config.h`)

- [ ] Mesurer le **diamètre des roues** au pied à coulisse → mettre à
      jour `WHEEL_DIAMETER_MM` (défaut : 90,0).
- [ ] Mesurer l'**entraxe** centre-à-centre entre les deux roues →
      mettre à jour `WHEEL_BASE_MM` (défaut : 120,0). Cette valeur a un
      impact direct sur la précision des rotations.
- [ ] Vérifier la valeur de `ENCODER_TICS_PER_REV` (700 par défaut). Pour
      la mesurer : marquer la roue, lancer `RESET_POSE` puis pousser la
      roue à la main pour faire exactement un tour, lire `GETENC`.

## D. Sens de rotation

- [ ] `TEST_MOTORS` : la roue gauche doit avancer en première phase, la
      roue droite ensuite. Si l'une part en arrière, mettre
      `MOTOR_LEFT_INVERT` ou `MOTOR_RIGHT_INVERT` à `true`.
- [ ] `TEST_ENCODERS` : tourner la roue gauche à la main vers l'avant ; le
      compteur doit augmenter. Si l'inverse, basculer
      `ENCODER_INVERT_LEFT`. Idem côté droit.

## E. Calibration capteurs

- [ ] **Gyroscope** : `CALIB_GYRO`, robot **immobile**, 5 s. Les offsets
      affichés doivent être faibles (< 1 °/s). Si supérieur, recommencer
      sur une surface vraiment stable.
- [ ] **Magnétomètre** : `CALIB_MAG`, environnement dégagé (pas d'objets
      métalliques à moins de 1 m, loin des moteurs en marche). Le robot
      tourne à 36 °/s pendant 10 s. Vérifier ensuite que `GETMAG` retourne
      un cap qui varie de manière monotone quand on tourne le robot
      manuellement à la main.

## F. PID vitesse roues

- [ ] `TEST_PWM_SWEEP` : noter le PWM de démarrage (vitesse > 0) et la
      vitesse atteinte à PWM = 1000. Adapter au besoin
      `MAX_LINEAR_SPEED_CM_S` dans `config.h`.
- [ ] `SETSPEED 600 600` puis observer Teleplot (`>speedL`, `>speedR`) :
      les courbes doivent rejoindre la consigne en < 200 ms sans
      dépassement > 20 %. Sinon ajuster `PID_SPEED_KP/KI` (`SETPID_SPEED`).

## G. PID pose (distance + cap)

- [ ] `RESET_POSE` puis `FORWARD 20` plusieurs fois : la position finale
      doit être à ±1 cm de la cible.
- [ ] `RESET_POSE` puis `LEFT 90` plusieurs fois : l'angle final doit être
      à ±5° de 90°.
- [ ] `RESET_POSE` puis `TEST_SQUARE` : l'erreur de fermeture (X, Y) doit
      rester sous ~2 cm.

## H. Séquences fonctionnelles

- [ ] `SEQ1` : escalier — comparer le tracé au schéma théorique.
- [ ] `SEQ2 10` : cercle Ø 20 cm — la fermeture doit être < 5 mm
      (cf. tolérance ET2.2 du cahier des charges).
- [ ] `SEQ3 8` : flèche orientée Nord — vérifier l'angle final avec une
      vraie boussole.

## I. Fonctionnalités avancées

- [ ] `SQUARES 5 3` (FA1) : 3 carrés circonscrits doivent partager
      l'origine.
- [ ] `ROSACE 8 6` (FA2) : 6 pétales équirépartis.
- [ ] `COMPASS 12` (FA3) : cercle Ø 12 cm + 8 directions + flèche Nord.

## J. Persistance des calibrations (à compléter)

- [ ] **TODO** : implémenter la sauvegarde des offsets gyro/mag et des
      gains PID en flash via `Preferences.h`. Les charger automatiquement
      au démarrage (à ajouter dans `setup()` après `imuInit()`/`magInit()`).
- [ ] **TODO** : ajouter une commande `SAVE_CONFIG` qui écrit les
      paramètres courants en flash.

---

## Diagnostic rapide

| Symptôme                                     | Cause probable                                |
|----------------------------------------------|-----------------------------------------------|
| Robot avance mais dérive de côté             | `WHEEL_BASE_MM` mauvais ou roues mal montées  |
| Carré ne se ferme pas (rotation en plus)     | `WHEEL_BASE_MM` trop petit                    |
| Rotation 90° donne 80° ou 100°               | `ENCODER_TICS_PER_REV` mauvais                |
| Cap magnéto chaotique                        | `CALIB_MAG` à refaire loin du métal           |
| Le robot oscille à l'arrêt                   | `PID_SPEED_KP` trop élevé                     |
| Distance trop courte avec dépassement        | `PID_DIST_KD` trop bas (ajouter de l'amortissement) |
