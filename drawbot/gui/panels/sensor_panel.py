"""
panels/sensor_panel.py
======================
Panneau [4] : Capteurs en temps réel (4 onglets).

  - IMU (LSM6DS3) : accéléro 3 axes, gyro 3 axes, niveau à bulle 2D
  - Magnétomètre (LIS3MDL) : composantes brutes, cap, boussole graphique
  - Encodeurs : RPM, tics, distance, jauge circulaire, graphique
  - Pose estimée : X, Y, θ, vitesses, dérive

Toutes les valeurs proviennent du ``FakeDataGenerator`` partagé. Un
``QTimer`` rafraîchit l'affichage toutes les 100 ms.

⚠ Aucune communication réelle. ``# TODO: brancher communication ESP32``
identifie les zones à câbler ultérieurement.
"""

import math
from collections import deque

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PyQt5.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from utils.fake_data import FakeDataGenerator
from utils.styles import COLORS


# Configuration globale pyqtgraph (fond sombre, police claire)
pg.setConfigOption("background", COLORS["bg_console"])
pg.setConfigOption("foreground", COLORS["text"])


# ---------------------------------------------------------------------------
# Petit widget niveau à bulle (cercle + point qui suit ax/ay)
# ---------------------------------------------------------------------------
class _BubbleLevel(QWidget):
    """Indicateur d'inclinaison 2D (à la manière d'un niveau à bulle)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(120, 120)
        self._ax = 0.0
        self._ay = 0.0

    def set_tilt(self, ax: float, ay: float) -> None:
        """Met à jour l'inclinaison affichée (en g, plage utile ±0.3)."""
        self._ax = max(-0.3, min(0.3, ax))
        self._ay = max(-0.3, min(0.3, ay))
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        size = min(self.width(), self.height()) - 8
        cx, cy = self.width() / 2, self.height() / 2
        r = size / 2

        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        painter.setBrush(QBrush(QColor(COLORS["bg_console"])))
        painter.drawEllipse(QPointF(cx, cy), r, r)
        painter.setPen(QPen(QColor(COLORS["border"]), 1, Qt.DashLine))
        painter.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
        painter.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))

        # Bulle (point central qui se déplace selon l'inclinaison)
        bx = cx + (self._ax / 0.3) * (r - 8)
        by = cy + (self._ay / 0.3) * (r - 8)
        painter.setBrush(QBrush(QColor(COLORS["primary"])))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(bx, by), 6, 6)


# ---------------------------------------------------------------------------
# Boussole graphique (cercle + aiguille rouge)
# ---------------------------------------------------------------------------
class _CompassWidget(QWidget):
    """Boussole graphique avec aiguille pointant vers le Nord magnétique."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(180, 180)
        self._heading_deg = 0.0

    def set_heading(self, deg: float) -> None:
        """Met à jour le cap (0° = Nord)."""
        self._heading_deg = deg
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        size = min(self.width(), self.height()) - 8
        cx, cy = self.width() / 2, self.height() / 2
        r = size / 2

        # Cercle de fond
        painter.setBrush(QBrush(QColor(COLORS["bg_console"])))
        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # Graduations + lettres cardinales
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        for k, label in enumerate(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]):
            angle = math.radians(k * 45 - 90)
            tx = cx + (r - 14) * math.cos(angle)
            ty = cy + (r - 14) * math.sin(angle)
            painter.setPen(QColor(COLORS["primary"] if label == "N" else COLORS["text_dim"]))
            painter.drawText(QRectF(tx - 12, ty - 10, 24, 20),
                             Qt.AlignCenter, label)

        # Aiguille
        # Le cap "0°" pointe vers N (haut). La pointe rouge représente le Nord
        # par rapport à l'orientation du robot : on dessine l'aiguille tournée
        # de -heading_deg autour du centre.
        painter.translate(cx, cy)
        painter.rotate(-self._heading_deg)
        painter.setBrush(QBrush(QColor(COLORS["danger"])))
        painter.setPen(Qt.NoPen)
        # Pointe Nord (rouge)
        painter.drawPolygon(QPointF(0, -r + 18), QPointF(-6, 0), QPointF(6, 0))
        # Queue Sud (gris)
        painter.setBrush(QBrush(QColor(COLORS["text_dim"])))
        painter.drawPolygon(QPointF(0, r - 18), QPointF(-6, 0), QPointF(6, 0))
        # Pivot central
        painter.setBrush(QBrush(QColor(COLORS["text"])))
        painter.drawEllipse(QPointF(0, 0), 4, 4)


# ---------------------------------------------------------------------------
# Onglet IMU
# ---------------------------------------------------------------------------
class _IMUTab(QWidget):
    def __init__(self, fake: FakeDataGenerator) -> None:
        super().__init__()
        self._fake = fake

        layout = QVBoxLayout(self)

        # --- Accéléromètre ---
        accel_box = QGroupBox("Accéléromètre")
        accel_layout = QVBoxLayout(accel_box)
        values_row = QHBoxLayout()
        self.lbl_ax = self._make_value_label("ax = +0.000 g")
        self.lbl_ay = self._make_value_label("ay = +0.000 g")
        self.lbl_az = self._make_value_label("az = +0.000 g")
        for lbl in (self.lbl_ax, self.lbl_ay, self.lbl_az):
            values_row.addWidget(lbl)
        accel_layout.addLayout(values_row)
        self.accel_plot = self._make_plot(["ax", "ay", "az"])
        accel_layout.addWidget(self.accel_plot["widget"])
        layout.addWidget(accel_box)

        # --- Gyroscope ---
        gyro_box = QGroupBox("Gyroscope")
        gyro_layout = QVBoxLayout(gyro_box)
        values_row = QHBoxLayout()
        self.lbl_gx = self._make_value_label("gx = +0.0 °/s")
        self.lbl_gy = self._make_value_label("gy = +0.0 °/s")
        self.lbl_gz = self._make_value_label("gz = +0.0 °/s")
        for lbl in (self.lbl_gx, self.lbl_gy, self.lbl_gz):
            values_row.addWidget(lbl)
        gyro_layout.addLayout(values_row)
        self.gyro_plot = self._make_plot(["gx", "gy", "gz"])
        gyro_layout.addWidget(self.gyro_plot["widget"])
        layout.addWidget(gyro_box)

        # --- Niveau à bulle ---
        tilt_box = QGroupBox("Inclinaison (roll/pitch)")
        tilt_layout = QHBoxLayout(tilt_box)
        self.bubble = _BubbleLevel()
        tilt_layout.addWidget(self.bubble)
        tilt_layout.addStretch()
        layout.addWidget(tilt_box)

        # Buffers pour les courbes (50 points = 5 s à 100 ms)
        self._buf_len = 50
        self._t_buf = deque(maxlen=self._buf_len)
        self._accel_buf = {k: deque(maxlen=self._buf_len) for k in ("ax", "ay", "az")}
        self._gyro_buf = {k: deque(maxlen=self._buf_len) for k in ("gx", "gy", "gz")}

    @staticmethod
    def _make_value_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("role", "value")
        return lbl

    @staticmethod
    def _make_plot(keys):
        """Crée un PlotWidget pyqtgraph avec une courbe par axe."""
        widget = pg.PlotWidget()
        widget.showGrid(x=True, y=True, alpha=0.3)
        widget.setMouseEnabled(x=False, y=False)
        widget.addLegend(offset=(-10, 10))
        colors = [COLORS["primary"], COLORS["success"], COLORS["warning"]]
        curves = {}
        for key, color in zip(keys, colors):
            curves[key] = widget.plot(pen=pg.mkPen(color, width=2), name=key)
        return {"widget": widget, "curves": curves}

    def update_values(self) -> None:
        """Lit le dernier échantillon et met à jour labels + courbes."""
        s = self._fake.last_imu
        self.lbl_ax.setText(f"ax = {s.ax:+.3f} g")
        self.lbl_ay.setText(f"ay = {s.ay:+.3f} g")
        self.lbl_az.setText(f"az = {s.az:+.3f} g")
        self.lbl_gx.setText(f"gx = {s.gx:+.1f} °/s")
        self.lbl_gy.setText(f"gy = {s.gy:+.1f} °/s")
        self.lbl_gz.setText(f"gz = {s.gz:+.1f} °/s")

        self._t_buf.append(s.timestamp)
        self._accel_buf["ax"].append(s.ax)
        self._accel_buf["ay"].append(s.ay)
        self._accel_buf["az"].append(s.az)
        self._gyro_buf["gx"].append(s.gx)
        self._gyro_buf["gy"].append(s.gy)
        self._gyro_buf["gz"].append(s.gz)

        if len(self._t_buf) >= 2:
            t = np.array(self._t_buf)
            t = t - t[-1]  # axe X relatif (s)
            for k, curve in self.accel_plot["curves"].items():
                curve.setData(t, np.array(self._accel_buf[k]))
            for k, curve in self.gyro_plot["curves"].items():
                curve.setData(t, np.array(self._gyro_buf[k]))

        self.bubble.set_tilt(s.ax, s.ay)


# ---------------------------------------------------------------------------
# Onglet Magnétomètre
# ---------------------------------------------------------------------------
class _MagTab(QWidget):
    def __init__(self, fake: FakeDataGenerator, log_callback) -> None:
        super().__init__()
        self._fake = fake
        self._log = log_callback

        layout = QVBoxLayout(self)

        # Valeurs brutes
        values_row = QHBoxLayout()
        self.lbl_mx = QLabel("mx = +0.0 µT"); self.lbl_mx.setProperty("role", "value")
        self.lbl_my = QLabel("my = +0.0 µT"); self.lbl_my.setProperty("role", "value")
        self.lbl_mz = QLabel("mz = +0.0 µT"); self.lbl_mz.setProperty("role", "value")
        for w in (self.lbl_mx, self.lbl_my, self.lbl_mz):
            values_row.addWidget(w)
        layout.addLayout(values_row)

        # Cap
        self.lbl_heading = QLabel("0° N")
        self.lbl_heading.setProperty("role", "big-value")
        self.lbl_heading.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_heading)

        # Boussole
        self.compass = _CompassWidget()
        compass_row = QHBoxLayout()
        compass_row.addStretch()
        compass_row.addWidget(self.compass)
        compass_row.addStretch()
        layout.addLayout(compass_row)

        # Calibration
        self.lbl_calib = QLabel("Calibration : Bonne ✓")
        self.lbl_calib.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
        layout.addWidget(self.lbl_calib)

        layout.addStretch()

    def update_values(self) -> None:
        s = self._fake.last_mag
        self.lbl_mx.setText(f"mx = {s.mx:+.1f} µT")
        self.lbl_my.setText(f"my = {s.my:+.1f} µT")
        self.lbl_mz.setText(f"mz = {s.mz:+.1f} µT")
        cardinal = _heading_to_cardinal(s.heading_deg)
        self.lbl_heading.setText(f"{s.heading_deg:.0f}° {cardinal}")
        self.compass.set_heading(s.heading_deg)


def _heading_to_cardinal(deg: float) -> str:
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[int((deg + 22.5) % 360 // 45)]


# ---------------------------------------------------------------------------
# Onglet Encodeurs
# ---------------------------------------------------------------------------
class _EncodersTab(QWidget):
    def __init__(self, fake: FakeDataGenerator) -> None:
        super().__init__()
        self._fake = fake

        layout = QVBoxLayout(self)
        wheels_row = QHBoxLayout()

        # Roue gauche
        left_box = QGroupBox("Roue gauche")
        left_layout = QVBoxLayout(left_box)
        self.lbl_left_rpm = QLabel("0 RPM"); self.lbl_left_rpm.setProperty("role", "big-value")
        self.lbl_left_ticks = QLabel("0 tics")
        self.lbl_left_dist = QLabel("0.000 m")
        left_layout.addWidget(self.lbl_left_rpm)
        left_layout.addWidget(self.lbl_left_ticks)
        left_layout.addWidget(self.lbl_left_dist)
        self.gauge_left = _CircularGauge()
        left_layout.addWidget(self.gauge_left)
        wheels_row.addWidget(left_box)

        # Roue droite
        right_box = QGroupBox("Roue droite")
        right_layout = QVBoxLayout(right_box)
        self.lbl_right_rpm = QLabel("0 RPM"); self.lbl_right_rpm.setProperty("role", "big-value")
        self.lbl_right_ticks = QLabel("0 tics")
        self.lbl_right_dist = QLabel("0.000 m")
        right_layout.addWidget(self.lbl_right_rpm)
        right_layout.addWidget(self.lbl_right_ticks)
        right_layout.addWidget(self.lbl_right_dist)
        self.gauge_right = _CircularGauge()
        right_layout.addWidget(self.gauge_right)
        wheels_row.addWidget(right_box)

        layout.addLayout(wheels_row)

        # Différentiel
        diff_box = QGroupBox("Différentiel G/D")
        diff_layout = QHBoxLayout(diff_box)
        self.lbl_delta = QLabel("ΔV = 0 RPM")
        self.lbl_state = QLabel("Ligne droite ✓")
        self.lbl_state.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
        diff_layout.addWidget(self.lbl_delta)
        diff_layout.addWidget(self.lbl_state)
        layout.addWidget(diff_box)

        # Graphique pyqtgraph (10 s glissantes = 100 points)
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.setLabel("left", "RPM")
        self.plot.setLabel("bottom", "t (s)")
        self.plot.addLegend(offset=(-10, 10))
        self.curve_left = self.plot.plot(pen=pg.mkPen(COLORS["primary"], width=2), name="G")
        self.curve_right = self.plot.plot(pen=pg.mkPen(COLORS["warning"], width=2), name="D")
        layout.addWidget(self.plot)

    def update_values(self) -> None:
        s = self._fake.last_encoder
        self.lbl_left_rpm.setText(f"{s.rpm_left:.0f} RPM")
        self.lbl_right_rpm.setText(f"{s.rpm_right:.0f} RPM")
        self.lbl_left_ticks.setText(f"{s.ticks_left} tics")
        self.lbl_right_ticks.setText(f"{s.ticks_right} tics")
        self.lbl_left_dist.setText(f"{s.dist_left:.3f} m")
        self.lbl_right_dist.setText(f"{s.dist_right:.3f} m")
        self.gauge_left.set_value(abs(s.rpm_left))
        self.gauge_right.set_value(abs(s.rpm_right))

        delta = s.rpm_left - s.rpm_right
        self.lbl_delta.setText(f"ΔV = {delta:+.0f} RPM")
        if abs(delta) < 5:
            self.lbl_state.setText("Ligne droite ✓")
            self.lbl_state.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
        else:
            self.lbl_state.setText("Tournant ↻")
            self.lbl_state.setStyleSheet(f"color: {COLORS['warning']}; font-weight: bold;")

        # Graphique
        history = self._fake.encoder_history
        if len(history) >= 2:
            t0 = history[-1].timestamp
            t = np.array([h.timestamp - t0 for h in history])
            self.curve_left.setData(t, np.array([h.rpm_left for h in history]))
            self.curve_right.setData(t, np.array([h.rpm_right for h in history]))


# ---------------------------------------------------------------------------
# Jauge circulaire (RPM)
# ---------------------------------------------------------------------------
class _CircularGauge(QWidget):
    """Jauge circulaire 0-100 RPM."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(120, 120)
        self._value = 0.0

    def set_value(self, v: float) -> None:
        """Fixe la valeur courante (clampée à 0-100)."""
        self._value = max(0.0, min(100.0, v))
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        size = min(self.width(), self.height()) - 16
        cx, cy = self.width() / 2, self.height() / 2
        rect = QRectF(cx - size / 2, cy - size / 2, size, size)

        painter.setPen(QPen(QColor(COLORS["bg_panel_alt"]), 8))
        painter.drawArc(rect, 225 * 16, -270 * 16)

        painter.setPen(QPen(QColor(COLORS["primary"]), 8))
        span = -270 * (self._value / 100)
        painter.drawArc(rect, 225 * 16, int(span * 16))

        painter.setPen(QColor(COLORS["text"]))
        painter.setFont(QFont("Consolas", 14, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, f"{self._value:.0f}")


# ---------------------------------------------------------------------------
# Onglet Pose estimée
# ---------------------------------------------------------------------------
class _PoseTab(QWidget):
    def __init__(self, fake: FakeDataGenerator) -> None:
        super().__init__()
        self._fake = fake

        layout = QVBoxLayout(self)
        self.lbl_x = QLabel("X = 0.00 cm"); self.lbl_x.setProperty("role", "big-value")
        self.lbl_y = QLabel("Y = 0.00 cm"); self.lbl_y.setProperty("role", "big-value")
        self.lbl_t = QLabel("θ = 0.0 °");   self.lbl_t.setProperty("role", "big-value")
        layout.addWidget(self.lbl_x)
        layout.addWidget(self.lbl_y)
        layout.addWidget(self.lbl_t)

        # Source de la pose
        row = QHBoxLayout()
        row.addWidget(QLabel("Source :"))
        self.combo_source = QComboBox()
        self.combo_source.addItems(
            ["Fusion (IMU + encodeurs)", "Encodeurs seuls", "IMU seule"]
        )
        row.addWidget(self.combo_source)
        row.addStretch()
        layout.addLayout(row)

        # Vitesses
        self.lbl_v = QLabel("v = 0.0 cm/s")
        self.lbl_w = QLabel("ω = 0.0 °/s")
        self.lbl_drift = QLabel("Dérive estimée : 0.0 cm/m")
        self.lbl_drift.setProperty("role", "dim")
        layout.addWidget(self.lbl_v)
        layout.addWidget(self.lbl_w)
        layout.addWidget(self.lbl_drift)

        layout.addStretch()

    def update_values(self) -> None:
        p = self._fake.pose
        self.lbl_x.setText(f"X = {p.x:+.2f} cm")
        self.lbl_y.setText(f"Y = {p.y:+.2f} cm")
        self.lbl_t.setText(f"θ = {p.theta_deg:+.1f} °")
        self.lbl_v.setText(f"v = {self._fake.state.linear_speed:+.1f} cm/s")
        self.lbl_w.setText(f"ω = {self._fake.state.angular_speed:+.1f} °/s")
        self.lbl_drift.setText("Dérive estimée : 0.3 cm/m")


# ---------------------------------------------------------------------------
# Panneau global (QTabWidget capteurs)
# ---------------------------------------------------------------------------
class SensorPanel(QGroupBox):
    """Panneau capteurs temps réel (4 onglets)."""

    def __init__(self, log_callback, fake: FakeDataGenerator, parent=None) -> None:
        super().__init__("Capteurs (temps réel)", parent)
        self._fake = fake

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tab_imu = _IMUTab(fake)
        self.tab_mag = _MagTab(fake, log_callback)
        self.tab_enc = _EncodersTab(fake)
        self.tab_pose = _PoseTab(fake)

        self.tabs.addTab(self.tab_imu, "IMU")
        self.tabs.addTab(self.tab_mag, "Magnétomètre")
        self.tabs.addTab(self.tab_enc, "Encodeurs")
        self.tabs.addTab(self.tab_pose, "Pose")

        # Timer de rafraîchissement (100 ms)
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(100)
        self._update_timer.timeout.connect(self._refresh_all)
        self._update_timer.start()

        # TODO: brancher communication ESP32 ici (recevoir les vraies trames
        # IMU, magnéto, encodeurs et pose au lieu de lire FakeDataGenerator)

    def _refresh_all(self) -> None:
        """Rafraîchit tous les onglets à partir du générateur factice."""
        self.tab_imu.update_values()
        self.tab_mag.update_values()
        self.tab_enc.update_values()
        self.tab_pose.update_values()
