"""
main_window.py
==============
Fenêtre principale du Drawbot Control Panel.

Assemble les six panneaux dans la grille suivante :

  [1] Bandeau connexion & statut (largeur totale)
  [2] Pilotage manuel  | [3] Séquences  | [4] Capteurs
  [5] Trajectoire 2D                    | [6] Console & logs

Crée également :
  - le générateur de données factices partagé (FakeDataGenerator) ;
  - le QTimer principal qui appelle ``tick()`` toutes les 100 ms ;
  - les menus (Fichier, Édition, Robot, Affichage, Aide) ;
  - la barre d'état du bas ;
  - les raccourcis clavier globaux (ZQSD, flèches, espace, P, Échap, F1, F11) ;
  - la persistance des préférences (taille de fenêtre, mode, adresse, thème)
    via QSettings et un fichier ``settings.json``.
"""

import json
import os
import time

from PyQt5.QtCore import Qt, QTimer, QSettings
from PyQt5.QtGui import QKeySequence, QIcon
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QShortcut,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from panels.connection_panel import ConnectionPanel
from panels.console_panel import ConsolePanel
from panels.manual_control_panel import ManualControlPanel
from panels.sensor_panel import SensorPanel
from panels.sequence_panel import SequencePanel
from panels.trajectory_panel import TrajectoryPanel
from utils.fake_data import FakeDataGenerator


SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


class MainWindow(QMainWindow):
    """Fenêtre principale, conteneur de tous les panneaux."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Drawbot Control Panel — v1.0")
        self.resize(1400, 900)
        self.setMinimumSize(1200, 800)

        # Icône de la fenêtre (icône PyQt par défaut faute de ressource)
        self.setWindowIcon(self.style().standardIcon(
            self.style().SP_ComputerIcon
        ))

        # Source unique de vérité pour les données capteurs/pose
        self._fake = FakeDataGenerator()

        # Construit l'UI dans l'ordre console → autres (la console est le
        # callback de tous les autres panneaux)
        self._build_central()
        self._build_menu()
        self._build_status_bar()
        self._setup_shortcuts()
        self._setup_signals()
        self._setup_timers()

        # Charge les préférences sauvegardées et écrit les logs initiaux
        self._load_settings()
        self._initial_logs()

    # ------------------------------------------------------------------
    # Construction de l'UI
    # ------------------------------------------------------------------
    def _build_central(self) -> None:
        """Construit la grille des 6 panneaux."""
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        # Console créée en premier pour être référencée comme callback
        self.console = ConsolePanel()
        log = self.console.log

        # [1] Bandeau connexion
        self.connection = ConnectionPanel(log)
        outer.addWidget(self.connection)

        # Ligne du milieu : 3 panneaux côte à côte
        middle = QHBoxLayout()
        middle.setSpacing(8)
        self.manual = ManualControlPanel(log, self._fake)
        self.sequences = SequencePanel(log, self._fake)
        self.sensors = SensorPanel(log, self._fake)
        middle.addWidget(self.manual, 2)
        middle.addWidget(self.sequences, 3)
        middle.addWidget(self.sensors, 3)
        outer.addLayout(middle, 3)

        # Ligne du bas : trajectoire + console
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self.trajectory = TrajectoryPanel(log, self._fake, manual_panel=self.manual)
        bottom.addWidget(self.trajectory, 1)
        bottom.addWidget(self.console, 1)
        outer.addLayout(bottom, 2)

    def _build_menu(self) -> None:
        """Construit la barre de menus principale."""
        menubar = self.menuBar()

        # Fichier
        file_menu = menubar.addMenu("&Fichier")
        act_new = QAction("Nouveau projet", self, shortcut="Ctrl+N")
        act_new.triggered.connect(self._action_new_project)
        act_open = QAction("Ouvrir préset…", self, shortcut="Ctrl+O")
        act_open.triggered.connect(lambda: self.console.log("INFO", "Ouverture préset (factice)"))
        act_save = QAction("Sauvegarder préset", self, shortcut="Ctrl+S")
        act_save.triggered.connect(lambda: self.console.log("INFO", "Préset sauvegardé (factice)"))
        file_menu.addAction(act_new)
        file_menu.addAction(act_open)
        file_menu.addAction(act_save)
        file_menu.addSeparator()
        export_menu = file_menu.addMenu("Exporter trajectoire")
        export_menu.addAction("PNG", self.trajectory._export_png)  # noqa: SLF001
        export_menu.addAction("SVG", self.trajectory._export_svg)  # noqa: SLF001
        export_menu.addAction("CSV",
                              lambda: self.console.log("INFO", "Export CSV (factice)"))
        file_menu.addSeparator()
        act_quit = QAction("Quitter", self, shortcut="Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # Édition
        edit_menu = menubar.addMenu("&Édition")
        edit_menu.addAction("Préférences…",
                            lambda: self.console.log("INFO", "Boîte préférences (factice)"))
        edit_menu.addAction("Réinitialiser interface", self._reset_ui)

        # Robot
        robot_menu = menubar.addMenu("&Robot")
        robot_menu.addAction(
            QAction("Connecter", self, shortcut="Ctrl+K",
                    triggered=self.connection._on_connect_clicked)  # noqa: SLF001
        )
        robot_menu.addAction(
            QAction("Déconnecter", self, shortcut="Ctrl+D",
                    triggered=self.connection._on_connect_clicked)  # noqa: SLF001
        )
        robot_menu.addSeparator()
        robot_menu.addAction("Calibrer IMU",
                             self.manual._on_calibrate_imu)  # noqa: SLF001
        robot_menu.addAction("Calibrer magnétomètre",
                             self.manual._on_calibrate_mag)  # noqa: SLF001
        robot_menu.addAction("Test moteurs",
                             lambda: self.console.log("INFO", "Test moteurs (factice)"))

        # Affichage : checkboxes pour montrer/cacher les panneaux
        view_menu = menubar.addMenu("&Affichage")
        for label, widget in [
            ("Bandeau statut", self.connection),
            ("Pilotage manuel", self.manual),
            ("Séquences", self.sequences),
            ("Capteurs", self.sensors),
            ("Trajectoire", self.trajectory),
            ("Console", self.console),
        ]:
            act = QAction(label, self, checkable=True, checked=True)
            act.toggled.connect(widget.setVisible)
            view_menu.addAction(act)
        view_menu.addSeparator()
        theme_group = QActionGroup(self)
        act_dark = QAction("Mode sombre", self, checkable=True, checked=True)
        act_light = QAction("Mode clair", self, checkable=True, checked=False)
        act_light.setEnabled(False)  # mode clair non implémenté
        theme_group.addAction(act_dark)
        theme_group.addAction(act_light)
        view_menu.addActions([act_dark, act_light])

        # Aide
        help_menu = menubar.addMenu("Aide")
        help_menu.addAction(QAction("Documentation", self, shortcut="F1",
                                    triggered=self._action_help))
        help_menu.addAction("Raccourcis clavier", self._action_shortcuts)
        help_menu.addAction("À propos…", self._action_about)

    def _build_status_bar(self) -> None:
        """Construit la barre d'état en bas avec quelques indicateurs."""
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.lbl_status_conn = QLabel("● Déconnecté")
        self.lbl_status_mode = QLabel("Mode : Aperçu")
        self.lbl_status_fps = QLabel("FPS : 60")
        self.lbl_status_mem = QLabel("Mémoire : 45 MB")
        self.lbl_status_clock = QLabel("--:--:--")
        for w in (self.lbl_status_conn, self.lbl_status_mode,
                  self.lbl_status_fps, self.lbl_status_mem,
                  self.lbl_status_clock):
            sb.addPermanentWidget(w)

    # ------------------------------------------------------------------
    # Raccourcis clavier
    # ------------------------------------------------------------------
    def _setup_shortcuts(self) -> None:
        """Mappe les raccourcis clavier globaux aux slots des panneaux."""
        # Avancer
        for keyseq in ("Z", "Up"):
            QShortcut(QKeySequence(keyseq), self,
                      activated=self.manual.move_forward)
        # Reculer
        for keyseq in ("S", "Down"):
            QShortcut(QKeySequence(keyseq), self,
                      activated=self.manual.move_backward)
        # Gauche
        for keyseq in ("Q", "Left"):
            QShortcut(QKeySequence(keyseq), self,
                      activated=self.manual.turn_left)
        # Droite
        for keyseq in ("D", "Right"):
            QShortcut(QKeySequence(keyseq), self,
                      activated=self.manual.turn_right)
        # Stop
        QShortcut(QKeySequence("Space"), self,
                  activated=self.manual.stop_motion)
        # Stylo
        QShortcut(QKeySequence("P"), self,
                  activated=self.manual.toggle_pen)
        # Arrêt d'urgence
        QShortcut(QKeySequence("Escape"), self,
                  activated=self.manual._on_emergency)  # noqa: SLF001
        # Plein écran
        QShortcut(QKeySequence("F11"), self,
                  activated=self._toggle_fullscreen)

    # ------------------------------------------------------------------
    # Signaux inter-panneaux
    # ------------------------------------------------------------------
    def _setup_signals(self) -> None:
        # Connexion : met à jour la barre d'état
        self.connection.connection_changed.connect(self._on_connection_changed)

        # Séquences → trajectoire (preview)
        self.sequences.preview_trajectory_requested.connect(
            self.trajectory.set_preview
        )
        self.sequences.sequence_finished.connect(self.trajectory.clear_preview)

        # Arrêt d'urgence : interrompt aussi les séquences
        self.manual.emergency_stopped.connect(self.sequences.stop_all)

    def _on_connection_changed(self, connected: bool) -> None:
        if connected:
            self.lbl_status_conn.setText("● Connecté")
            self.lbl_status_conn.setStyleSheet("color: #4ade80;")
        else:
            self.lbl_status_conn.setText("● Déconnecté")
            self.lbl_status_conn.setStyleSheet("color: #ef4444;")

    # ------------------------------------------------------------------
    # Timers
    # ------------------------------------------------------------------
    def _setup_timers(self) -> None:
        # Tick principal du générateur factice (100 ms)
        self._main_timer = QTimer(self)
        self._main_timer.setInterval(100)
        self._main_timer.timeout.connect(self._fake.tick)
        self._main_timer.start()

        # Horloge en barre d'état (1 s)
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start()
        self._update_clock()

    def _update_clock(self) -> None:
        self.lbl_status_clock.setText(time.strftime("%H:%M:%S"))

    # ------------------------------------------------------------------
    # Actions de menu
    # ------------------------------------------------------------------
    def _action_new_project(self) -> None:
        self.trajectory._clear_trajectory()  # noqa: SLF001
        self._fake.reset_pose()
        self.console.log("INFO", "Nouveau projet : trajectoire et pose réinitialisées")

    def _action_help(self) -> None:
        QMessageBox.information(
            self, "Documentation",
            "Drawbot Control Panel — interface de pilotage en mode Aperçu.\n\n"
            "Aucune communication avec le robot n'est actuellement établie. "
            "Tous les contrôles loggent leurs actions dans la console."
        )

    def _action_shortcuts(self) -> None:
        QMessageBox.information(
            self, "Raccourcis clavier",
            "Z / ↑ : avancer\n"
            "S / ↓ : reculer\n"
            "Q / ← : tourner gauche\n"
            "D / → : tourner droite\n"
            "Espace : STOP\n"
            "P : toggle stylo\n"
            "Échap : arrêt d'urgence\n"
            "Ctrl+N : nouveau projet\n"
            "Ctrl+S : sauvegarder préset\n"
            "Ctrl+K / Ctrl+D : connexion / déconnexion\n"
            "F1 : aide\n"
            "F11 : plein écran"
        )

    def _action_about(self) -> None:
        QMessageBox.about(
            self, "À propos",
            "<h3>Drawbot Control Panel</h3>"
            "<p>Version 1.0 — interface graphique seule (mode Aperçu).</p>"
            "<p>Robot Drawbot : ESP32 + IMU LSM6DS3 + magnétomètre LIS3MDL "
            "+ 2 moteurs N20.</p>"
            "<p>Les boutons sont fonctionnels visuellement uniquement, "
            "aucune communication réelle n'est faite.</p>"
        )

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _reset_ui(self) -> None:
        self.resize(1400, 900)
        self.console.log("INFO", "Interface réinitialisée")

    # ------------------------------------------------------------------
    # Logs initiaux
    # ------------------------------------------------------------------
    def _initial_logs(self) -> None:
        log = self.console.log
        log("INFO", "GUI Drawbot v1.0 démarrée")
        log("INFO", "Mode : Aperçu (pas de communication)")
        log("INFO", "Tous les contrôles sont fonctionnels visuellement")
        log("WARNING", "Robot non connecté")
        log("INFO", "En attente d'instructions utilisateur...")

    # ------------------------------------------------------------------
    # Persistance (settings.json)
    # ------------------------------------------------------------------
    def _load_settings(self) -> None:
        """Charge les préférences depuis settings.json (sans bloquer si absent)."""
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as err:
            self.console.log("WARNING", f"Impossible de lire settings.json : {err}")
            return

        geom = data.get("window", {})
        if "width" in geom and "height" in geom:
            self.resize(int(geom["width"]), int(geom["height"]))
        if "x" in geom and "y" in geom:
            self.move(int(geom["x"]), int(geom["y"]))
        if "mode" in data:
            idx = self.connection.mode_combo.findText(data["mode"])
            if idx >= 0:
                self.connection.mode_combo.setCurrentIndex(idx)
        if "address" in data:
            self.connection.address_edit.setText(data["address"])

    def _save_settings(self) -> None:
        """Sauvegarde les préférences dans settings.json."""
        data = {
            "window": {
                "x": self.x(), "y": self.y(),
                "width": self.width(), "height": self.height(),
            },
            "mode": self.connection.mode_combo.currentText(),
            "address": self.connection.address_edit.text(),
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
        except OSError as err:
            self.console.log("ERROR", f"Échec sauvegarde settings : {err}")

    # ------------------------------------------------------------------
    # Surcharge fermeture
    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802
        """Sauvegarde les préférences avant la fermeture."""
        self._save_settings()
        super().closeEvent(event)
