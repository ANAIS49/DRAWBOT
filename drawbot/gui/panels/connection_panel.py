"""
panels/connection_panel.py
==========================
Panneau [1] : Bandeau de connexion & statut.

Contient :
  - sélection du mode de connexion (WiFi TCP/UDP, Bluetooth, Série)
  - champ adresse IP / port COM (selon le mode)
  - bouton Connecter/Déconnecter avec animation de la LED
  - latence simulée
  - indicateur batterie (décroissance lente)
  - bouton Rafraîchir

⚠ AUCUNE communication réelle n'est faite. Tous les callbacks sont visuels
et écrivent dans la console de logs. Les zones marquées
``# TODO: brancher communication ESP32`` indiquent où câbler la couche
réseau ultérieurement.
"""

import random

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from utils.styles import COLORS


# ---------------------------------------------------------------------------
# Widget LED de statut (cercle coloré peint à la main)
# ---------------------------------------------------------------------------
class StatusLED(QWidget):
    """Petit indicateur circulaire coloré (rouge / orange / vert)."""

    STATES = {
        "off":     QColor(COLORS["danger"]),
        "pending": QColor(COLORS["warning"]),
        "on":      QColor(COLORS["success"]),
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._state = "off"
        self._blink_on = True

        # Timer de clignotement pour l'état "pending"
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(250)
        self._blink_timer.timeout.connect(self._toggle_blink)

    def set_state(self, state: str) -> None:
        """Change l'état visuel : off | pending | on."""
        if state not in self.STATES:
            return
        self._state = state
        if state == "pending":
            self._blink_timer.start()
        else:
            self._blink_timer.stop()
            self._blink_on = True
        self.update()

    def _toggle_blink(self) -> None:
        """Alterne la visibilité du point pour produire un clignotement."""
        self._blink_on = not self._blink_on
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt convention)
        """Dessine le cercle coloré centré dans le widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = self.STATES[self._state]
        if self._state == "pending" and not self._blink_on:
            color = QColor(COLORS["bg_panel_alt"])
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 12, 12)


# ---------------------------------------------------------------------------
# Panneau principal
# ---------------------------------------------------------------------------
class ConnectionPanel(QGroupBox):
    """Bandeau horizontal de connexion et statut système."""

    # Signaux émis vers la fenêtre principale (pour piloter d'autres panneaux)
    connection_changed = pyqtSignal(bool)   # True = connecté

    def __init__(self, log_callback, parent=None) -> None:
        """
        :param log_callback: fonction(level, msg) appelée pour journaliser.
        :param parent: widget parent.
        """
        super().__init__("Connexion & statut", parent)
        self._log = log_callback
        self._connected = False
        self._battery_level = 85

        self._build_ui()
        self._setup_timers()

    # ------------------------------------------------------------------
    # Construction de l'UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setSpacing(10)

        # --- Mode de connexion ---
        layout.addWidget(QLabel("Mode :"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["WiFi (TCP)", "WiFi (UDP)", "Bluetooth", "Série USB"])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        layout.addWidget(self.mode_combo)

        # --- Adresse IP ---
        layout.addWidget(QLabel("Adresse :"))
        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("192.168.1.100:8080")
        self.address_edit.setFixedWidth(180)
        layout.addWidget(self.address_edit)

        # --- Port COM ---
        layout.addWidget(QLabel("Port COM :"))
        self.com_combo = QComboBox()
        self.com_combo.addItems(["COM3", "COM4", "COM5"])
        self.com_combo.setEnabled(False)
        layout.addWidget(self.com_combo)

        # --- Bouton Connecter ---
        self.connect_button = QPushButton("Connecter")
        self.connect_button.setProperty("variant", "success")
        self.connect_button.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self.connect_button)

        # --- LED ---
        self.led = StatusLED()
        layout.addWidget(self.led)

        # --- Latence ---
        self.latency_label = QLabel("Latence : -- ms")
        self.latency_label.setMinimumWidth(110)
        layout.addWidget(self.latency_label)

        # --- Séparateur visuel ---
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color: {COLORS['border']};")
        layout.addWidget(sep)

        # --- Batterie ---
        layout.addWidget(QLabel("🔋"))
        self.battery_bar = QProgressBar()
        self.battery_bar.setRange(0, 100)
        self.battery_bar.setValue(self._battery_level)
        self.battery_bar.setFixedWidth(100)
        layout.addWidget(self.battery_bar)
        self.battery_label = QLabel(f"{self._battery_level}%")
        self.battery_label.setMinimumWidth(40)
        layout.addWidget(self.battery_label)
        self._update_battery_color()

        layout.addStretch()

        # --- Bouton Rafraîchir ---
        self.refresh_button = QPushButton("🔄 Rafraîchir")
        self.refresh_button.clicked.connect(self._on_refresh_clicked)
        layout.addWidget(self.refresh_button)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(80)

    # ------------------------------------------------------------------
    # Timers (latence, batterie, animation connexion)
    # ------------------------------------------------------------------
    def _setup_timers(self) -> None:
        # Mise à jour aléatoire de la latence (5-50 ms) quand connecté
        self._latency_timer = QTimer(self)
        self._latency_timer.setInterval(1000)
        self._latency_timer.timeout.connect(self._update_latency)

        # Décroissance batterie de 1% toutes les 30 s
        self._battery_timer = QTimer(self)
        self._battery_timer.setInterval(30_000)
        self._battery_timer.timeout.connect(self._decrement_battery)
        self._battery_timer.start()

        # Timer de fin d'animation "connexion en cours"
        self._connect_anim_timer = QTimer(self)
        self._connect_anim_timer.setSingleShot(True)
        self._connect_anim_timer.setInterval(1500)
        self._connect_anim_timer.timeout.connect(self._finish_connection)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _on_mode_changed(self, mode: str) -> None:
        """Active/désactive les champs selon le mode choisi."""
        is_wifi = mode.startswith("WiFi")
        is_serial = mode == "Série USB"
        self.address_edit.setEnabled(is_wifi)
        self.com_combo.setEnabled(is_serial)
        self._log("INFO", f"Mode de connexion changé : {mode}")

    def _on_connect_clicked(self) -> None:
        """Toggle Connecter/Déconnecter avec animation visuelle."""
        if not self._connected:
            # Lancement de la connexion (animation : rouge → orange → vert)
            self.led.set_state("pending")
            self.connect_button.setEnabled(False)
            self._log("INFO", "Tentative de connexion en cours...")
            self._log("TX", "CONNECT — handshake en cours")
            # TODO: brancher communication ESP32 ici
            #   → ouvrir socket TCP / UDP / série / BT selon self.mode_combo,
            #     puis appeler self._finish_connection() en cas de succès.
            self._connect_anim_timer.start()
        else:
            # Déconnexion immédiate
            # TODO: brancher communication ESP32 ici
            #   → fermer la connexion réseau / série établie.
            self._connected = False
            self.led.set_state("off")
            self.connect_button.setText("Connecter")
            self.connect_button.setProperty("variant", "success")
            self.connect_button.style().unpolish(self.connect_button)
            self.connect_button.style().polish(self.connect_button)
            self.latency_label.setText("Latence : -- ms")
            self._latency_timer.stop()
            self._log("WARNING", "Déconnecté du robot")
            self.connection_changed.emit(False)

    def _finish_connection(self) -> None:
        """Fin de l'animation de connexion : passage à l'état connecté."""
        self._connected = True
        self.led.set_state("on")
        self.connect_button.setText("Déconnecter")
        self.connect_button.setProperty("variant", "danger")
        self.connect_button.style().unpolish(self.connect_button)
        self.connect_button.style().polish(self.connect_button)
        self.connect_button.setEnabled(True)
        self._latency_timer.start()
        self._log("SUCCESS", "Connecté au robot (simulé)")
        self.connection_changed.emit(True)

    def _on_refresh_clicked(self) -> None:
        """Réinitialise visuellement le bandeau (sans toucher à la batterie)."""
        self._log("INFO", "Rafraîchissement de l'état système")
        if self._connected:
            self.latency_label.setText("Latence : -- ms")

    # ------------------------------------------------------------------
    # Mises à jour périodiques
    # ------------------------------------------------------------------
    def _update_latency(self) -> None:
        """Met à jour le label de latence avec une valeur aléatoire."""
        ms = random.randint(5, 50)
        self.latency_label.setText(f"Latence : {ms} ms")

    def _decrement_battery(self) -> None:
        """Décroît la charge de batterie de 1%, plancher à 0."""
        if self._battery_level > 0:
            self._battery_level -= 1
            self.battery_bar.setValue(self._battery_level)
            self.battery_label.setText(f"{self._battery_level}%")
            self._update_battery_color()
            if self._battery_level == 20:
                self._log("WARNING", "Batterie faible (20%)")
            elif self._battery_level == 10:
                self._log("ERROR", "Batterie critique (10%)")

    def _update_battery_color(self) -> None:
        """Adapte la couleur de la barre de batterie à son niveau."""
        if self._battery_level > 50:
            color = COLORS["success"]
        elif self._battery_level > 20:
            color = COLORS["warning"]
        else:
            color = COLORS["danger"]
        self.battery_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
        )

    # ------------------------------------------------------------------
    # Accesseurs
    # ------------------------------------------------------------------
    def is_connected(self) -> bool:
        """Indique si la connexion (simulée) est active."""
        return self._connected
