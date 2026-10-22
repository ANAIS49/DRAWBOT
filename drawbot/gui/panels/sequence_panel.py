"""
panels/sequence_panel.py
========================
Panneau [3] : Séquences de dessin.

Trois onglets, un par séquence :
  - Séquence 1 — Escalier  (+ FA1 : carrés circonscrits)
  - Séquence 2 — Cercle     (+ FA2 : rosace)
  - Séquence 3 — Rose des vents (+ FA3 : rose complète)

Chaque onglet propose des paramètres (QSpinBox / QSlider / RadioButton),
des actions (Lancer / Pause / Stop / Sauver / Charger) et une barre de
progression simulée. Lors du clic sur "Lancer", la trajectoire théorique
est calculée et publiée via le signal ``preview_trajectory_requested``
pour être tracée par le panneau de trajectoire ; pendant l'exécution
factice, ``run_step`` met à jour la pose dans le générateur factice.

⚠ Aucune communication réelle. ``# TODO: brancher communication ESP32``
identifie les zones à câbler ultérieurement.
"""

import math
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from utils.fake_data import FakeDataGenerator
from utils.styles import COLORS


# ---------------------------------------------------------------------------
# Aperçu graphique générique (QWidget peint en QPainter)
# ---------------------------------------------------------------------------
class _PreviewWidget(QWidget):
    """
    Widget de prévisualisation 2D pour les séquences. Reçoit une liste de
    points (x, y) en cm, qu'il auto-cadre dans la zone disponible.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(100)
        self._points: List[Tuple[float, float]] = []

    def set_points(self, points: List[Tuple[float, float]]) -> None:
        """Met à jour la liste de points à dessiner et redessine."""
        self._points = points
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(COLORS["bg_console"]))
        if not self._points:
            return

        # Détermine la bbox des points pour auto-cadrer
        xs = [p[0] for p in self._points]
        ys = [p[1] for p in self._points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1)
        span_y = max(max_y - min_y, 1)

        margin = 10
        w = self.width() - 2 * margin
        h = self.height() - 2 * margin
        scale = min(w / span_x, h / span_y)

        def to_screen(pt: Tuple[float, float]) -> QPointF:
            x = margin + (pt[0] - min_x) * scale
            y = self.height() - margin - (pt[1] - min_y) * scale
            return QPointF(x, y)

        pen = QPen(QColor(COLORS["primary"]))
        pen.setWidth(2)
        painter.setPen(pen)
        for i in range(len(self._points) - 1):
            painter.drawLine(to_screen(self._points[i]), to_screen(self._points[i + 1]))

        # Marqueur de départ
        painter.setBrush(QBrush(QColor(COLORS["success"])))
        painter.setPen(Qt.NoPen)
        p0 = to_screen(self._points[0])
        painter.drawEllipse(p0, 4, 4)


# ---------------------------------------------------------------------------
# Génération des trajectoires théoriques
# ---------------------------------------------------------------------------
def build_staircase_trajectory(
    seg1: float, ang1: float, seg2: float, ang2: float, seg3: float
) -> List[Tuple[float, float]]:
    """Construit la trajectoire théorique de la séquence 1 (escalier)."""
    points = [(0.0, 0.0)]
    x, y, theta = 0.0, 0.0, 0.0
    for length, turn in [(seg1, ang1), (seg2, ang2), (seg3, 0)]:
        x += length * math.cos(math.radians(theta))
        y += length * math.sin(math.radians(theta))
        points.append((x, y))
        theta += turn
    return points


def build_circle_trajectory(radius: float, n_points: int = 64) -> List[Tuple[float, float]]:
    """Construit la trajectoire d'un cercle de rayon donné."""
    return [
        (radius * math.cos(2 * math.pi * i / n_points),
         radius * math.sin(2 * math.pi * i / n_points))
        for i in range(n_points + 1)
    ]


def build_rosace_trajectory(radius: float, petals: int) -> List[Tuple[float, float]]:
    """Construit une rosace (cercle + pétales) approximative pour aperçu."""
    pts: List[Tuple[float, float]] = []
    n = 200
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        r = radius * math.cos(petals * t)
        pts.append((r * math.cos(t), r * math.sin(t)))
    return pts


def build_arrow_trajectory(length: float, head_width: float) -> List[Tuple[float, float]]:
    """Construit une flèche orientée vers le haut (cap nord)."""
    return [
        (0.0, 0.0),
        (0.0, length),
        (-head_width / 2, length - head_width),
        (0.0, length),
        (head_width / 2, length - head_width),
    ]


# ---------------------------------------------------------------------------
# Onglet de séquence générique
# ---------------------------------------------------------------------------
class _SequenceTab(QWidget):
    """
    Sous-classe abstraite : structure commune pour chaque onglet.
    Les enfants définissent ``_build_params()`` et ``compute_trajectory()``.
    """

    sequence_started = pyqtSignal(list)   # liste de points (x, y) en cm
    sequence_finished = pyqtSignal()

    def __init__(self, name: str, log_callback, fake: FakeDataGenerator) -> None:
        super().__init__()
        self.name = name
        self._log = log_callback
        self._fake = fake
        self._running = False
        self._paused = False

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setSpacing(8)

        # Description (à surcharger)
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self._main_layout.addWidget(self.description_label)

        # Aperçu graphique
        self.preview = _PreviewWidget()
        self._main_layout.addWidget(self.preview)

        # Zone paramètres (remplie par les enfants)
        self.params_form = QFormLayout()
        params_box = QGroupBox("Paramètres")
        params_box.setLayout(self.params_form)
        self._main_layout.addWidget(params_box)

        # Boutons d'action
        actions = QHBoxLayout()
        self.btn_start = QPushButton("▶ Lancer")
        self.btn_start.setProperty("variant", "success")
        self.btn_start.clicked.connect(self._on_start)
        actions.addWidget(self.btn_start)

        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setProperty("variant", "warning")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._on_pause)
        actions.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹ Arrêter")
        self.btn_stop.setProperty("variant", "danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop)
        actions.addWidget(self.btn_stop)

        self.btn_save = QPushButton("💾 Sauvegarder préset")
        self.btn_save.clicked.connect(self._on_save_preset)
        actions.addWidget(self.btn_save)

        self.btn_load = QPushButton("📁 Charger préset")
        self.btn_load.clicked.connect(self._on_load_preset)
        actions.addWidget(self.btn_load)
        self._main_layout.addLayout(actions)

        # Barre de progression
        progress_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_label = QLabel("Inactif")
        progress_row.addWidget(self.progress_bar, 1)
        progress_row.addWidget(self.progress_label, 1)
        self._main_layout.addLayout(progress_row)

        # Timer d'animation factice (mise à jour ~10 fois/s pendant 10 s)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(100)
        self._anim_timer.timeout.connect(self._tick_animation)
        self._anim_step = 0
        self._anim_total = 100
        self._traj_points: List[Tuple[float, float]] = []
        self._anim_steps_text: List[str] = []

    # ----- À surcharger par les enfants -----
    def compute_trajectory(self) -> List[Tuple[float, float]]:
        raise NotImplementedError

    def step_descriptions(self) -> List[str]:
        """Retourne la liste de descriptions de chaque étape (pour les logs)."""
        return [f"Étape {i+1}" for i in range(5)]

    # ----- Actions -----
    def _on_start(self) -> None:
        if self._running:
            return
        self._traj_points = self.compute_trajectory()
        self._anim_steps_text = self.step_descriptions()
        self.sequence_started.emit(self._traj_points)
        self._log("TX", f"Commande envoyée : {self.name.upper()}")
        # TODO: brancher communication ESP32 ici (envoi de la séquence)
        self._running = True
        self._paused = False
        self._anim_step = 0
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self._anim_timer.start()

    def _on_pause(self) -> None:
        if not self._running:
            return
        self._paused = not self._paused
        if self._paused:
            self._anim_timer.stop()
            self.btn_pause.setText("▶ Reprendre")
            self._log("INFO", f"{self.name} mise en pause")
            # TODO: brancher communication ESP32 ici (commande PAUSE)
        else:
            self._anim_timer.start()
            self.btn_pause.setText("⏸ Pause")
            self._log("INFO", f"{self.name} reprise")
            # TODO: brancher communication ESP32 ici (commande RESUME)

    def _on_stop(self) -> None:
        if not self._running:
            return
        self._anim_timer.stop()
        self._running = False
        self._paused = False
        self._fake.stop()
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("⏸ Pause")
        self.btn_stop.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Arrêté")
        self._log("WARNING", f"{self.name} interrompue par l'utilisateur")
        # TODO: brancher communication ESP32 ici (commande STOP)
        self.sequence_finished.emit()

    def _on_save_preset(self) -> None:
        self._log("INFO", f"Préset {self.name} sauvegardé (factice)")
        # TODO: sérialiser les paramètres en JSON sur disque

    def _on_load_preset(self) -> None:
        self._log("INFO", f"Préset {self.name} chargé (factice)")
        # TODO: charger un fichier JSON et appliquer les paramètres

    def _tick_animation(self) -> None:
        """Avance d'un tic l'animation factice (10 s au total)."""
        self._anim_step += 1
        pct = int(100 * self._anim_step / self._anim_total)
        self.progress_bar.setValue(pct)

        # Log d'étape de temps en temps
        n_steps = max(1, len(self._anim_steps_text))
        current_step_idx = min(
            n_steps - 1,
            int(self._anim_step / self._anim_total * n_steps),
        )
        step_text = self._anim_steps_text[current_step_idx] if self._anim_steps_text else ""
        self.progress_label.setText(
            f"{pct}% — Étape {current_step_idx + 1}/{n_steps} : {step_text}"
        )

        # Déplacement factice du robot le long de la trajectoire théorique
        if self._traj_points:
            idx = min(
                len(self._traj_points) - 1,
                int(self._anim_step / self._anim_total * (len(self._traj_points) - 1)),
            )
            x, y = self._traj_points[idx]
            self._fake.pose.x = x
            self._fake.pose.y = y
            if idx + 1 < len(self._traj_points):
                nx, ny = self._traj_points[idx + 1]
                dx, dy = nx - x, ny - y
                if dx or dy:
                    self._fake.pose.theta_deg = math.degrees(math.atan2(dy, dx))

        if self._anim_step >= self._anim_total:
            self._anim_timer.stop()
            self._running = False
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.progress_label.setText("Terminé ✓")
            self._log("SUCCESS", f"{self.name} terminée")
            self.sequence_finished.emit()


# ---------------------------------------------------------------------------
# Onglet 1 : Escalier
# ---------------------------------------------------------------------------
class _StaircaseTab(_SequenceTab):
    def __init__(self, log_callback, fake: FakeDataGenerator) -> None:
        super().__init__("Séquence 1 — Escalier", log_callback, fake)
        self.description_label.setText(
            "Le robot avance, tourne, et trace un escalier en 5 segments."
        )
        self._build_params()
        self._refresh_preview()

    def _build_params(self) -> None:
        self.spin_seg1 = QSpinBox(); self.spin_seg1.setRange(5, 100); self.spin_seg1.setValue(20)
        self.spin_ang1 = QSpinBox(); self.spin_ang1.setRange(-180, 180); self.spin_ang1.setValue(90)
        self.spin_seg2 = QSpinBox(); self.spin_seg2.setRange(5, 100); self.spin_seg2.setValue(10)
        self.spin_ang2 = QSpinBox(); self.spin_ang2.setRange(-180, 180); self.spin_ang2.setValue(-90)
        self.spin_seg3 = QSpinBox(); self.spin_seg3.setRange(5, 100); self.spin_seg3.setValue(40)

        for w in (self.spin_seg1, self.spin_ang1, self.spin_seg2,
                  self.spin_ang2, self.spin_seg3):
            w.valueChanged.connect(self._refresh_preview)

        self.params_form.addRow("Longueur segment 1 (cm) :", self.spin_seg1)
        self.params_form.addRow("Angle 1 (°) :", self.spin_ang1)
        self.params_form.addRow("Longueur segment 2 (cm) :", self.spin_seg2)
        self.params_form.addRow("Angle 2 (°) :", self.spin_ang2)
        self.params_form.addRow("Longueur segment 3 (cm) :", self.spin_seg3)

        # Mode avancé FA1
        self.fa1_box = QGroupBox("Mode avancé : carrés circonscrits (FA1)")
        self.fa1_box.setCheckable(True)
        self.fa1_box.setChecked(False)
        fa1_form = QFormLayout(self.fa1_box)
        self.spin_fa1_len = QSpinBox(); self.spin_fa1_len.setRange(2, 30); self.spin_fa1_len.setValue(5)
        self.spin_fa1_n = QSpinBox(); self.spin_fa1_n.setRange(2, 20); self.spin_fa1_n.setValue(5)
        fa1_form.addRow("Longueur 1er segment (cm) :", self.spin_fa1_len)
        fa1_form.addRow("Nombre de carrés :", self.spin_fa1_n)
        fa1_form.addRow(QLabel(
            "<i>La longueur de chaque carré augmente de la longueur du segment initial.</i>"
        ))
        self._main_layout.insertWidget(self._main_layout.count() - 2, self.fa1_box)

    def compute_trajectory(self) -> List[Tuple[float, float]]:
        if self.fa1_box.isChecked():
            return self._compute_fa1()
        return build_staircase_trajectory(
            self.spin_seg1.value(), self.spin_ang1.value(),
            self.spin_seg2.value(), self.spin_ang2.value(),
            self.spin_seg3.value(),
        )

    def _compute_fa1(self) -> List[Tuple[float, float]]:
        """Construit une suite de carrés circonscrits (FA1)."""
        base = self.spin_fa1_len.value()
        n = self.spin_fa1_n.value()
        x, y, theta = 0.0, 0.0, 0.0
        pts = [(x, y)]
        for k in range(1, n + 1):
            side = base * k
            for _ in range(4):
                x += side * math.cos(math.radians(theta))
                y += side * math.sin(math.radians(theta))
                pts.append((x, y))
                theta += 90
        return pts

    def step_descriptions(self) -> List[str]:
        return [
            f"Avancer {self.spin_seg1.value()} cm",
            f"Tourner {self.spin_ang1.value()}°",
            f"Avancer {self.spin_seg2.value()} cm",
            f"Tourner {self.spin_ang2.value()}°",
            f"Avancer {self.spin_seg3.value()} cm",
        ]

    def _refresh_preview(self) -> None:
        self.preview.set_points(self.compute_trajectory())


# ---------------------------------------------------------------------------
# Onglet 2 : Cercle
# ---------------------------------------------------------------------------
class _CircleTab(_SequenceTab):
    def __init__(self, log_callback, fake: FakeDataGenerator) -> None:
        super().__init__("Séquence 2 — Cercle", log_callback, fake)
        self.description_label.setText(
            "Le robot trace un cercle de rayon paramétrable."
        )
        self._build_params()
        self._refresh_preview()

    def _build_params(self) -> None:
        self.spin_radius = QDoubleSpinBox()
        self.spin_radius.setRange(2.0, 20.0)
        self.spin_radius.setSingleStep(0.5)
        self.spin_radius.setValue(10.0)
        self.spin_radius.setSuffix(" cm")
        self.spin_radius.valueChanged.connect(self._refresh_preview)

        self.radio_cw = QRadioButton("Horaire")
        self.radio_ccw = QRadioButton("Antihoraire")
        self.radio_cw.setChecked(True)
        sense_row = QHBoxLayout()
        sense_row.addWidget(self.radio_cw)
        sense_row.addWidget(self.radio_ccw)
        sense_widget = QWidget()
        sense_widget.setLayout(sense_row)

        self.combo_speed = QComboBox()
        self.combo_speed.addItems(["Lente", "Normale", "Rapide"])
        self.combo_speed.setCurrentText("Normale")

        self.spin_turns = QSpinBox()
        self.spin_turns.setRange(1, 5)
        self.spin_turns.setValue(1)

        self.params_form.addRow("Rayon du cercle :", self.spin_radius)
        self.params_form.addRow("Sens de rotation :", sense_widget)
        self.params_form.addRow("Vitesse de tracé :", self.combo_speed)
        self.params_form.addRow("Nombre de tours :", self.spin_turns)

        # Mode avancé FA2 — rosace
        self.fa2_box = QGroupBox("Mode avancé : rosace (FA2)")
        self.fa2_box.setCheckable(True)
        self.fa2_box.setChecked(False)
        fa2_form = QFormLayout(self.fa2_box)
        self.spin_petals = QSpinBox(); self.spin_petals.setRange(4, 12); self.spin_petals.setValue(6)
        self.spin_petals.valueChanged.connect(self._refresh_preview)
        self.check_link_radius = QCheckBox("Rayon des pétales lié au rayon principal")
        self.check_link_radius.setChecked(True)
        self.check_link_radius.toggled.connect(self._on_link_toggled)
        self.spin_petal_radius = QDoubleSpinBox()
        self.spin_petal_radius.setRange(2.0, 20.0)
        self.spin_petal_radius.setSingleStep(0.5)
        self.spin_petal_radius.setValue(10.0)
        self.spin_petal_radius.setEnabled(False)
        self.spin_petal_radius.valueChanged.connect(self._refresh_preview)
        fa2_form.addRow("Nombre de pétales :", self.spin_petals)
        fa2_form.addRow("Rayon des pétales :", self.spin_petal_radius)
        fa2_form.addRow(self.check_link_radius)
        self.fa2_box.toggled.connect(self._refresh_preview)
        self._main_layout.insertWidget(self._main_layout.count() - 2, self.fa2_box)

        # Tolérances
        tol_label = QLabel("Tolérances : Ø ±5 mm  |  Fermeture ±5 mm")
        tol_label.setProperty("role", "dim")
        self._main_layout.insertWidget(self._main_layout.count() - 2, tol_label)

    def _on_link_toggled(self, linked: bool) -> None:
        self.spin_petal_radius.setEnabled(not linked)
        if linked:
            self.spin_petal_radius.setValue(self.spin_radius.value())
        self._refresh_preview()

    def compute_trajectory(self) -> List[Tuple[float, float]]:
        if self.fa2_box.isChecked():
            r = (self.spin_radius.value()
                 if self.check_link_radius.isChecked()
                 else self.spin_petal_radius.value())
            return build_rosace_trajectory(r, self.spin_petals.value())
        return build_circle_trajectory(self.spin_radius.value())

    def step_descriptions(self) -> List[str]:
        if self.fa2_box.isChecked():
            return [
                "Positionnement initial",
                f"Tracé rosace ({self.spin_petals.value()} pétales)",
                "Retour à l'origine",
            ]
        steps = [
            "Positionnement initial",
            f"Tracé cercle (R={self.spin_radius.value()} cm)",
        ]
        steps.extend(f"Tour {i + 1}" for i in range(self.spin_turns.value()))
        return steps

    def _refresh_preview(self) -> None:
        if self.fa2_box.isChecked() and self.check_link_radius.isChecked():
            self.spin_petal_radius.setValue(self.spin_radius.value())
        self.preview.set_points(self.compute_trajectory())


# ---------------------------------------------------------------------------
# Onglet 3 : Rose des vents
# ---------------------------------------------------------------------------
class _CompassTab(_SequenceTab):
    def __init__(self, log_callback, fake: FakeDataGenerator) -> None:
        super().__init__("Séquence 3 — Rose des vents", log_callback, fake)
        self.description_label.setText(
            "Le robot dessine une flèche ou une rose des vents complète "
            "orientée vers le Nord magnétique."
        )
        self._build_params()
        self._refresh_preview()

    def _build_params(self) -> None:
        # Mode (flèche simple ou rose complète)
        self.radio_arrow = QRadioButton("Flèche simple")
        self.radio_full = QRadioButton("Rose des vents complète (FA3)")
        self.radio_arrow.setChecked(True)
        self.radio_arrow.toggled.connect(self._on_mode_changed)
        mode_row = QHBoxLayout()
        mode_row.addWidget(self.radio_arrow)
        mode_row.addWidget(self.radio_full)
        mode_widget = QWidget()
        mode_widget.setLayout(mode_row)
        self.params_form.addRow("Mode :", mode_widget)

        # Paramètres communs
        self.spin_length = QDoubleSpinBox()
        self.spin_length.setRange(3.0, 30.0); self.spin_length.setSingleStep(0.5); self.spin_length.setValue(5.0)
        self.spin_length.valueChanged.connect(self._refresh_preview)
        self.params_form.addRow("Longueur (cm) :", self.spin_length)

        self.spin_head = QDoubleSpinBox()
        self.spin_head.setRange(0.5, 5.0); self.spin_head.setSingleStep(0.1); self.spin_head.setValue(1.5)
        self.spin_head.valueChanged.connect(self._refresh_preview)
        self.params_form.addRow("Largeur de la pointe (cm) :", self.spin_head)

        self.check_filled = QCheckBox()
        self.check_filled.setChecked(True)
        self.params_form.addRow("Triangle plein :", self.check_filled)

        self.slider_density = QSlider(Qt.Horizontal)
        self.slider_density.setRange(50, 100)
        self.slider_density.setValue(80)
        self.params_form.addRow("Densité de remplissage (%) :", self.slider_density)

        # Paramètres FA3
        self.fa3_box = QGroupBox("Paramètres FA3 — rose complète")
        fa3_form = QFormLayout(self.fa3_box)
        self.spin_circle_d = QDoubleSpinBox()
        self.spin_circle_d.setRange(5.0, 25.0); self.spin_circle_d.setValue(10.0)
        self.spin_circle_d.valueChanged.connect(self._refresh_preview)
        self.check_8dirs = QCheckBox(); self.check_8dirs.setChecked(True)
        self.check_mark_n = QCheckBox(); self.check_mark_n.setChecked(True)
        fa3_form.addRow("Diamètre du cercle (cm) :", self.spin_circle_d)
        fa3_form.addRow("8 directions (N, NE, E, SE, S, SW, W, NW) :", self.check_8dirs)
        fa3_form.addRow("Marquer le N de façon distinctive :", self.check_mark_n)
        self.fa3_box.setVisible(False)
        self._main_layout.insertWidget(self._main_layout.count() - 2, self.fa3_box)

        # État magnéto
        mag_box = QGroupBox("État du magnétomètre")
        mag_layout = QVBoxLayout(mag_box)
        self.mag_label = QLabel("Cap actuel : -- ° (--)")
        self.last_calib_label = QLabel("Dernière calibration : il y a 12 min")
        self.last_calib_label.setProperty("role", "dim")
        btn_recal = QPushButton("🧭 Recalibrer maintenant")
        btn_recal.clicked.connect(lambda: self._log(
            "INFO", "Calibration magnétomètre lancée"))
        mag_layout.addWidget(self.mag_label)
        mag_layout.addWidget(self.last_calib_label)
        mag_layout.addWidget(btn_recal)
        self._main_layout.insertWidget(self._main_layout.count() - 2, mag_box)

        # Timer pour rafraîchir le cap (lit le générateur factice)
        self._cap_timer = QTimer(self)
        self._cap_timer.setInterval(500)
        self._cap_timer.timeout.connect(self._refresh_cap_label)
        self._cap_timer.start()

    def _on_mode_changed(self) -> None:
        self.fa3_box.setVisible(self.radio_full.isChecked())
        self._refresh_preview()

    def _refresh_cap_label(self) -> None:
        h = self._fake.last_mag.heading_deg
        cardinal = _to_cardinal(h)
        self.mag_label.setText(f"Cap actuel : {h:.0f}° ({cardinal})")

    def compute_trajectory(self) -> List[Tuple[float, float]]:
        if self.radio_full.isChecked():
            return self._build_full_compass()
        return build_arrow_trajectory(self.spin_length.value(), self.spin_head.value())

    def _build_full_compass(self) -> List[Tuple[float, float]]:
        """Cercle + 8 traits cardinaux pour la rose complète (FA3)."""
        r = self.spin_circle_d.value() / 2
        pts = build_circle_trajectory(r, 64)
        if self.check_8dirs.isChecked():
            for k in range(8):
                a = math.radians(k * 45 + 90)  # 0 = N, sens trigo
                pts.append((0, 0))
                pts.append((r * math.cos(a), r * math.sin(a)))
        # Flèche du N
        pts.extend([(0, 0)] + build_arrow_trajectory(
            self.spin_length.value(), self.spin_head.value()))
        return pts

    def step_descriptions(self) -> List[str]:
        if self.radio_full.isChecked():
            return [
                "Tracé cercle extérieur",
                "Tracé direction N (mise en évidence)",
                "Tracé directions NE/E/SE/S/SW/W/NW",
                "Retour à l'origine",
            ]
        return ["Positionnement", "Tracé hampe", "Tracé pointe"]

    def _refresh_preview(self) -> None:
        self.preview.set_points(self.compute_trajectory())


def _to_cardinal(deg: float) -> str:
    """Convertit un cap en degrés en symbole cardinal (N, NE, E, ...)."""
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[int((deg + 22.5) % 360 // 45)]


# ---------------------------------------------------------------------------
# Panneau global (QTabWidget)
# ---------------------------------------------------------------------------
class SequencePanel(QGroupBox):
    """Panneau regroupant les trois onglets de séquences de dessin."""

    # Émis quand un onglet veut afficher sa trajectoire théorique
    preview_trajectory_requested = pyqtSignal(list)
    sequence_finished = pyqtSignal()

    def __init__(self, log_callback, fake: FakeDataGenerator, parent=None) -> None:
        super().__init__("Séquences de dessin", parent)
        self._log = log_callback
        self._fake = fake

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tab_staircase = _StaircaseTab(log_callback, fake)
        self.tab_circle = _CircleTab(log_callback, fake)
        self.tab_compass = _CompassTab(log_callback, fake)

        for tab in (self.tab_staircase, self.tab_circle, self.tab_compass):
            tab.sequence_started.connect(self.preview_trajectory_requested)
            tab.sequence_finished.connect(self.sequence_finished)

        self.tabs.addTab(self.tab_staircase, "Escalier")
        self.tabs.addTab(self.tab_circle, "Cercle")
        self.tabs.addTab(self.tab_compass, "Rose des vents")

    def stop_all(self) -> None:
        """Arrête immédiatement toute séquence en cours (arrêt d'urgence)."""
        for tab in (self.tab_staircase, self.tab_circle, self.tab_compass):
            if tab._running:  # noqa: SLF001 (accès interne assumé)
                tab._on_stop()
