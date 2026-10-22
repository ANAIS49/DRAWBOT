# Drawbot Control Panel

Interface graphique de pilotage du robot **Drawbot** (ESP32 + 2 moteurs N20
+ IMU LSM6DS3 + magnétomètre LIS3MDL).

> ⚠ **Mode Aperçu** : cette version n'établit **aucune communication réelle**
> avec le robot. Tous les boutons et contrôles sont fonctionnels visuellement
> et écrivent leurs actions dans la console intégrée. Les zones marquées
> `# TODO: brancher communication ESP32` indiquent les points où câbler la
> couche réseau ultérieurement (WiFi TCP/UDP, Bluetooth ou Série USB).

---

## Fonctionnalités

- **Bandeau de connexion & statut** : choix du mode (WiFi TCP/UDP, BT, Série),
  LED de statut animée, latence simulée, indicateur batterie.
- **Pilotage manuel** : croix directionnelle, sliders de vitesse, toggle stylo,
  reset position, calibration IMU/magnétomètre, ARRÊT D'URGENCE pleine largeur.
- **Séquences de dessin** (3 onglets) :
  - *Escalier* (+ FA1 carrés circonscrits)
  - *Cercle* (+ FA2 rosace)
  - *Rose des vents* (+ FA3 rose complète)
- **Capteurs temps réel** (4 onglets) : IMU, magnétomètre + boussole graphique,
  encodeurs avec jauges, pose estimée.
- **Visualisation 2D** : carte avec grille mm, trajectoire, tracé du stylo,
  preview de séquence, zoom/pan, export PNG/SVG, choix de couleur et épaisseur.
- **Console & logs** : niveaux colorés (INFO/SUCCESS/WARNING/ERROR/DEBUG/TX/RX),
  filtres, recherche, export `.txt`, pause auto-scroll.
- **Menus, barre d'état, raccourcis clavier globaux**, persistance des
  préférences dans `settings.json`.

## Captures d'écran

*(captures à ajouter — placeholder)*

## Prérequis

- Python 3.9 ou supérieur
- Voir `requirements.txt` :
  - PyQt5 ≥ 5.15
  - pyqtgraph ≥ 0.13
  - numpy ≥ 1.21

## Installation

```bash
cd gui
python -m venv .venv
source .venv/bin/activate     # Linux / macOS
# .venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Lancement

```bash
python main.py
```

## Arborescence

```
gui/
├── main.py                       # point d'entrée
├── main_window.py                # fenêtre principale
├── requirements.txt
├── README.md
├── panels/
│   ├── __init__.py
│   ├── connection_panel.py       # [1] bandeau de connexion
│   ├── manual_control_panel.py   # [2] pilotage manuel
│   ├── sequence_panel.py         # [3] séquences de dessin
│   ├── sensor_panel.py           # [4] capteurs temps réel
│   ├── trajectory_panel.py       # [5] visualisation trajectoire
│   └── console_panel.py          # [6] console & logs
└── utils/
    ├── __init__.py
    ├── fake_data.py              # générateur de données factices
    └── styles.py                 # thème QSS centralisé
```

## Raccourcis clavier

| Touche      | Action              |
|-------------|---------------------|
| Z / ↑       | Avancer             |
| S / ↓       | Reculer             |
| Q / ←       | Tourner gauche      |
| D / →       | Tourner droite      |
| Espace      | STOP                |
| P           | Stylo levé/baissé   |
| Échap       | Arrêt d'urgence     |
| Ctrl+N      | Nouveau projet      |
| Ctrl+S      | Sauvegarder préset  |
| Ctrl+K      | Connecter           |
| Ctrl+D      | Déconnecter         |
| F1          | Aide                |
| F11         | Plein écran         |

## TODO — Branchement futur de la communication

Tous les commentaires `# TODO: brancher communication ESP32` marquent les
endroits stratégiques où câbler la couche réseau réelle :

- [`panels/connection_panel.py`](panels/connection_panel.py)
  - `_on_connect_clicked` : ouverture/fermeture du socket TCP/UDP/BT/série
- [`panels/manual_control_panel.py`](panels/manual_control_panel.py)
  - `_start_motion` : commandes `MOVE_FORWARD` / `MOVE_BACKWARD` /
    `TURN_LEFT` / `TURN_RIGHT`
  - `_on_pen_toggled` : commande servo stylo
  - `_on_reset_position`, `_on_calibrate_imu`, `_on_calibrate_mag`,
    `_on_emergency`
- [`panels/sequence_panel.py`](panels/sequence_panel.py)
  - `_on_start` / `_on_pause` / `_on_stop` : envoi/pause/arrêt de la séquence
- [`panels/sensor_panel.py`](panels/sensor_panel.py)
  - `SensorPanel._refresh_all` : remplacer la lecture du `FakeDataGenerator`
    par la consommation des trames reçues (IMU, magnéto, encodeurs, pose)

## Contraintes respectées

- Aucun import de `pyserial`, `socket`, `requests`, `paho.mqtt`, `websocket`…
- Aucun appel réseau réel.
- Aucun accès matériel.
- Fonctionne offline et sans aucun robot connecté.
- Pas d'erreur Python au lancement, interface fluide.
