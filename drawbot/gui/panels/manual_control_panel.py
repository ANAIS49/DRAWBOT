"""
panels/manual_control_panel.py
==============================
Panneau [2] : Pilotage manuel du Drawbot.

Comprend :
  - Une croix directionnelle (Avancer / Reculer / Gauche / Droite + STOP)
  - Sliders de vitesse linéaire et angulaire
  - Toggle stylo levé/baissé
  - Boutons de reset position et calibration
  - Bouton ARRÊT D'URGENCE pleine largeur
  - Raccourcis clavier (ZQSD / flèches / espace / P / Échap) gérés par
    la fenêtre principale qui appelle les slots publics ci-dessous.

Aucune communication réelle : chaque action loggue dans la console et
met à jour le ``FakeDataGenerator`` partagé pour faire bouger le robot
sur la carte.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from utils.fake_data import FakeDataGenerator


# Vitesse maximale (commandes 100% sur les sliders)
MAX_LINEAR_SPEED = 20.0   # cm/s
MAX_ANGULAR_SPEED = 90.0  # °/s


class ManualControlPanel(QGroupBox):
    """Panneau de pilotage manuel + arrêt d'urgence."""

    # Signal émis quand l'utilisateur déclenche un arrêt d'urgence
    emergency_stopped = pyqtSignal()

    def __init__(self, log_callback, fake_data: FakeDataGenerator, parent=None) -> None:
        super().__init__("Pilotage manuel", parent)
        self._log = log_callback
        self._fake = fake_data

        self._linear_pct = 50
        self._angular_pct = 30
        self._pen_down = False

        self._build_ui()

    # ------------------------------------------------------------------
    # Construction de l'UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Croix directionnelle ---
        cross = QGridLayout()
        cross.setSpacing(4)

        self.btn_forward = self._make_dir_button("▲\nAvancer")
        self.btn_left = self._make_dir_button("◄\nGauche")
        self.btn_right = self._make_dir_button("Droite\n►")
        self.btn_back = self._make_dir_button("▼\nReculer")
        self.btn_stop = self._make_dir_button("⏹\nSTOP")
        self.btn_stop.setProperty("variant", "danger")

        cross.addWidget(self.btn_forward, 0, 1)
        cross.addWidget(self.btn_left,    1, 0)
        cross.addWidget(self.btn_stop,    1, 1)
        cross.addWidget(self.btn_right,   1, 2)
        cross.addWidget(self.btn_back,    2, 1)
        layout.addLayout(cross)

        # Connexion des boutons (press = action continue, release = stop)
        self.btn_forward.pressed.connect(lambda: self._start_motion("forward"))
        self.btn_forward.released.connect(self._stop_motion)
        self.btn_back.pressed.connect(lambda: self._start_motion("backward"))
        self.btn_back.released.connect(self._stop_motion)
        self.btn_left.pressed.connect(lambda: self._start_motion("left"))
        self.btn_left.released.connect(self._stop_motion)
        self.btn_right.pressed.connect(lambda: self._start_motion("right"))
        self.btn_right.released.connect(self._stop_motion)
        self.btn_stop.clicked.connect(self.stop_motion)

        # --- Slider vitesse linéaire ---
        layout.addWidget(QLabel("Vitesse de déplacement"))
        row = QHBoxLayout()
        self.linear_slider = QSlider(Qt.Horizontal)
        self.linear_slider.setRange(0, 100)
        self.linear_slider.setValue(self._linear_pct)
        self.linear_slider.setTickPosition(QSlider.TicksBelow)
        self.linear_slider.setTickInterval(10)
        self.linear_slider.valueChanged.connect(self._on_linear_changed)
        self.linear_value_label = QLabel(f"{self._linear_pct} %")
        self.linear_value_label.setMinimumWidth(40)
        row.addWidget(self.linear_slider, 1)
        row.addWidget(self.linear_value_label)
        layout.addLayout(row)

        # --- Slider vitesse angulaire ---
        layout.addWidget(QLabel("Vitesse de rotation"))
        row = QHBoxLayout()
        self.angular_slider = QSlider(Qt.Horizontal)
        self.angular_slider.setRange(0, 100)
        self.angular_slider.setValue(self._angular_pct)
        self.angular_slider.setTickPosition(QSlider.TicksBelow)
        self.angular_slider.setTickInterval(10)
        self.angular_slider.valueChanged.connect(self._on_angular_changed)
        self.angular_value_label = QLabel(f"{self._angular_pct} %")
        self.angular_value_label.setMinimumWidth(40)
        row.addWidget(self.angular_slider, 1)
        row.addWidget(self.angular_value_label)
        layout.addLayout(row)

        # --- Stylo ---
        pen_box = QGroupBox("Stylo")
        pen_layout = QVBoxLayout(pen_box)
        self.pen_button = QPushButton("✏️ Stylo levé")
        self.pen_button.setCheckable(True)
        self.pen_button.toggled.connect(self._on_pen_toggled)
        pen_layout.addWidget(self.pen_button)
        layout.addWidget(pen_box)

        # --- Position & calibration ---
        pos_box = QGroupBox("Position")
        pos_layout = QVBoxLayout(pos_box)
        self.reset_button = QPushButton("📍 Reset position (0, 0, 0°)")
        self.reset_button.clicked.connect(self._on_reset_position)
        pos_layout.addWidget(self.reset_button)

        self.calib_imu_button = QPushButton("📐 Calibrer orientation (IMU)")
        self.calib_imu_button.clicked.connect(self._on_calibrate_imu)
        pos_layout.addWidget(self.calib_imu_button)

        self.calib_mag_button = QPushButton("🧭 Calibrer magnétomètre")
        self.calib_mag_button.clicked.connect(self._on_calibrate_mag)
        pos_layout.addWidget(self.calib_mag_button)
        layout.addWidget(pos_box)

        layout.addStretch()

        # --- Arrêt d'urgence ---
        self.emergency_button = QPushButton("🚨 ARRÊT D'URGENCE")
        self.emergency_button.setProperty("variant", "emergency")
        self.emergency_button.setFixedHeight(50)
        self.emergency_button.clicked.connect(self._on_emergency)
        layout.addWidget(self.emergency_button)

    @staticmethod
    def _make_dir_button(text: str) -> QPushButton:
        """Crée un bouton directionnel 60×60 px formaté."""
        btn = QPushButton(text)
        btn.setFixedSize(70, 60)
        return btn

    # ------------------------------------------------------------------
    # Slots de mouvement (publics pour les raccourcis clavier)
    # ------------------------------------------------------------------
    def move_forward(self) -> None:
        """Démarre une avance (raccourci clavier Z / ↑)."""
        self._start_motion("forward")

    def move_backward(self) -> None:
        """Démarre un recul (raccourci clavier S / ↓)."""
        self._start_motion("backward")

    def turn_left(self) -> None:
        """Démarre une rotation à gauche (raccourci Q / ←)."""
        self._start_motion("left")

    def turn_right(self) -> None:
        """Démarre une rotation à droite (raccourci D / →)."""
        self._start_motion("right")

    def stop_motion(self) -> None:
        """Arrête tout mouvement (bouton STOP, espace)."""
        self._fake.stop()
        self._log("TX", "STOP")

    def toggle_pen(self) -> None:
        """Inverse l'état du stylo (raccourci P)."""
        self.pen_button.toggle()

    # ------------------------------------------------------------------
    # Implémentations privées
    # ------------------------------------------------------------------
    def _start_motion(self, direction: str) -> None:
        """Applique au générateur de données la commande directionnelle."""
        v = MAX_LINEAR_SPEED * self._linear_pct / 100
        w = MAX_ANGULAR_SPEED * self._angular_pct / 100

        if direction == "forward":
            self._fake.set_linear_speed(v)
            self._fake.set_angular_speed(0)
            self._log("TX", f"MOVE_FORWARD vitesse={self._linear_pct}")
            # TODO: brancher communication ESP32 ici (commande MOVE_FORWARD)
        elif direction == "backward":
            self._fake.set_linear_speed(-v)
            self._fake.set_angular_speed(0)
            self._log("TX", f"MOVE_BACKWARD vitesse={self._linear_pct}")
            # TODO: brancher communication ESP32 ici (commande MOVE_BACKWARD)
        elif direction == "left":
            self._fake.set_linear_speed(0)
            self._fake.set_angular_speed(w)
            self._log("TX", f"TURN_LEFT vitesse={self._angular_pct}")
            # TODO: brancher communication ESP32 ici (commande TURN_LEFT)
        elif direction == "right":
            self._fake.set_linear_speed(0)
            self._fake.set_angular_speed(-w)
            self._log("TX", f"TURN_RIGHT vitesse={self._angular_pct}")
            # TODO: brancher communication ESP32 ici (commande TURN_RIGHT)

    def _stop_motion(self) -> None:
        """Stop interne (release des boutons fléchés)."""
        self.stop_motion()

    def _on_linear_changed(self, value: int) -> None:
        self._linear_pct = value
        self.linear_value_label.setText(f"{value} %")

    def _on_angular_changed(self, value: int) -> None:
        self._angular_pct = value
        self.angular_value_label.setText(f"{value} %")

    def _on_pen_toggled(self, checked: bool) -> None:
        """Met à jour l'état du stylo (visuel + générateur factice)."""
        self._pen_down = checked
        self._fake.set_pen(checked)
        if checked:
            self.pen_button.setText("✏️ Stylo baissé")
            self.pen_button.setProperty("variant", "success")
            self._log("TX", "PEN_DOWN")
            # TODO: brancher communication ESP32 ici (servo stylo)
        else:
            self.pen_button.setText("✏️ Stylo levé")
            self.pen_button.setProperty("variant", "")
            self._log("TX", "PEN_UP")
            # TODO: brancher communication ESP32 ici (servo stylo)
        self.pen_button.style().unpolish(self.pen_button)
        self.pen_button.style().polish(self.pen_button)

    def _on_reset_position(self) -> None:
        self._fake.reset_pose()
        self._log("INFO", "Position remise à (0, 0, 0°)")
        # TODO: brancher communication ESP32 ici (commande RESET_POSE)

    def _on_calibrate_imu(self) -> None:
        self._log("INFO", "Calibration IMU lancée — laisser le robot immobile")
        # TODO: brancher communication ESP32 ici (commande CALIB_IMU)

    def _on_calibrate_mag(self) -> None:
        self._log(
            "INFO",
            "Calibration magnétomètre — le robot va tourner sur 360°"
        )
        # TODO: brancher communication ESP32 ici (commande CALIB_MAG)

    def _on_emergency(self) -> None:
        """Action sur l'arrêt d'urgence : log critique + signal global."""
        self._fake.stop()
        self._log("ERROR", "🚨 ARRÊT D'URGENCE déclenché par l'utilisateur")
        self._log("TX", "EMERGENCY_STOP")
        # TODO: brancher communication ESP32 ici (commande EMERGENCY_STOP prioritaire)
        self.emergency_stopped.emit()

    # ------------------------------------------------------------------
    # Accesseurs
    # ------------------------------------------------------------------
    def is_pen_down(self) -> bool:
        """Indique si le stylo est actuellement baissé."""
        return self._pen_down
