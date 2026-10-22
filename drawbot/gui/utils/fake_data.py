"""
utils/fake_data.py
==================
Générateur de données factices simulant la télémétrie du robot Drawbot.
Produit des valeurs plausibles pour l'accéléromètre, le gyroscope, le
magnétomètre, les encodeurs et la pose, à partir de l'état (vitesse,
direction) commandé par la GUI.

Aucune communication réelle n'est faite — toutes les valeurs sont issues
de bruit gaussien et d'une intégration mathématique simple.
"""

from dataclasses import dataclass, field
from typing import List
import math
import random
import time


# ---------------------------------------------------------------------------
# Structures de données
# ---------------------------------------------------------------------------
@dataclass
class IMUSample:
    """Échantillon IMU LSM6DS3 : accéléro 3 axes (g) + gyro 3 axes (°/s)."""
    ax: float
    ay: float
    az: float
    gx: float
    gy: float
    gz: float
    timestamp: float


@dataclass
class MagSample:
    """Échantillon magnétomètre LIS3MDL (µT) + cap calculé en degrés."""
    mx: float
    my: float
    mz: float
    heading_deg: float
    timestamp: float


@dataclass
class EncoderSample:
    """Échantillon encodeurs : vitesse (RPM), tics cumulés et distance (m)."""
    rpm_left: float
    rpm_right: float
    ticks_left: int
    ticks_right: int
    dist_left: float
    dist_right: float
    timestamp: float


@dataclass
class Pose:
    """Pose 2D du robot dans le repère monde (cm, cm, °)."""
    x: float = 0.0
    y: float = 0.0
    theta_deg: float = 0.0


@dataclass
class RobotState:
    """État de commande appliqué au robot (sliders + boutons)."""
    linear_speed: float = 0.0   # cm/s, signe = sens
    angular_speed: float = 0.0  # °/s, signe = sens
    pen_down: bool = False


# ---------------------------------------------------------------------------
# Générateur principal
# ---------------------------------------------------------------------------
class FakeDataGenerator:
    """
    Générateur centralisé de données factices.

    Appeler ``tick()`` à intervalle régulier (typiquement 100 ms) pour mettre
    à jour les échantillons internes ; les autres consommateurs lisent les
    propriétés ``last_imu``, ``last_mag``, ``last_encoder`` et ``pose``.
    """

    def __init__(self) -> None:
        self.state = RobotState()
        self.pose = Pose()

        # Cap magnétique simulé (tourne lentement quand le robot ne tourne pas)
        self._heading_drift_deg = 0.0

        # Cumuls encodeurs
        self._ticks_left = 0
        self._ticks_right = 0
        self._dist_left = 0.0
        self._dist_right = 0.0

        # Historiques pour les tracés (fenêtres glissantes)
        self.imu_history: List[IMUSample] = []
        self.encoder_history: List[EncoderSample] = []
        self._max_history = 100  # ~10 s à 100 ms

        # Derniers échantillons publics
        self.last_imu = IMUSample(0, 0, 0.98, 0, 0, 0, time.time())
        self.last_mag = MagSample(20, -10, 40, 0, time.time())
        self.last_encoder = EncoderSample(0, 0, 0, 0, 0, 0, time.time())

        self._last_tick = time.time()

    # ------------------------------------------------------------------
    # Commandes (appelées depuis les panneaux)
    # ------------------------------------------------------------------
    def set_linear_speed(self, cm_per_s: float) -> None:
        """Fixe la vitesse linéaire commandée (cm/s, signe = sens)."""
        self.state.linear_speed = cm_per_s

    def set_angular_speed(self, deg_per_s: float) -> None:
        """Fixe la vitesse angulaire commandée (°/s, signe = sens)."""
        self.state.angular_speed = deg_per_s

    def set_pen(self, down: bool) -> None:
        """Met à jour l'état du stylo."""
        self.state.pen_down = down

    def stop(self) -> None:
        """Arrête immédiatement le robot (vitesses à zéro)."""
        self.state.linear_speed = 0.0
        self.state.angular_speed = 0.0

    def reset_pose(self) -> None:
        """Réinitialise la pose à l'origine."""
        self.pose = Pose()

    # ------------------------------------------------------------------
    # Tick principal (à appeler par QTimer)
    # ------------------------------------------------------------------
    def tick(self) -> None:
        """Met à jour tous les échantillons à partir de l'état courant."""
        now = time.time()
        dt = now - self._last_tick
        self._last_tick = now
        if dt <= 0 or dt > 1:
            dt = 0.1

        # 1. Intégration de la pose à partir des vitesses commandées
        v = self.state.linear_speed              # cm/s
        omega = math.radians(self.state.angular_speed)  # rad/s
        theta_rad = math.radians(self.pose.theta_deg)
        self.pose.x += v * math.cos(theta_rad) * dt
        self.pose.y += v * math.sin(theta_rad) * dt
        self.pose.theta_deg = (
            self.pose.theta_deg + self.state.angular_speed * dt
        ) % 360

        # 2. Accéléromètre : gravité + petites secousses
        # az ~ 0.98 g (gravité), ax/ay = bruit + accélération longitudinale
        ax = random.gauss(0, 0.03) + 0.002 * v
        ay = random.gauss(0, 0.03)
        az = random.gauss(0.98, 0.03)

        # 3. Gyroscope : bruit + vitesse angulaire commandée sur z
        gx = random.gauss(0, 1.5)
        gy = random.gauss(0, 1.5)
        gz = self.state.angular_speed + random.gauss(0, 1.0)

        self.last_imu = IMUSample(ax, ay, az, gx, gy, gz, now)
        self.imu_history.append(self.last_imu)
        if len(self.imu_history) > self._max_history:
            self.imu_history.pop(0)

        # 4. Magnétomètre : cap = orientation robot + dérive lente
        if abs(self.state.angular_speed) < 0.1:
            self._heading_drift_deg = (self._heading_drift_deg + 1.0 * dt) % 360
        heading = (self.pose.theta_deg + self._heading_drift_deg * 0.05) % 360
        # Composantes mx/my représentent le champ horizontal (~ 25 µT)
        mx = 25 * math.cos(math.radians(heading)) + random.gauss(0, 0.5)
        my = -25 * math.sin(math.radians(heading)) + random.gauss(0, 0.5)
        mz = 40 + random.gauss(0, 0.5)
        self.last_mag = MagSample(mx, my, mz, heading, now)

        # 5. Encodeurs : vitesse de chaque roue déduite de v et omega
        # Modèle différentiel simple, entraxe = 12 cm, rayon roue = 3.4 cm
        wheel_base = 12.0
        wheel_radius = 3.4
        v_left = v - omega * wheel_base / 2
        v_right = v + omega * wheel_base / 2
        rpm_left = (v_left / (2 * math.pi * wheel_radius)) * 60
        rpm_right = (v_right / (2 * math.pi * wheel_radius)) * 60
        # Tics par tour ~ 700 (encodeur Hall N20 typique)
        ticks_per_rev = 700
        self._ticks_left += int(rpm_left * dt / 60 * ticks_per_rev)
        self._ticks_right += int(rpm_right * dt / 60 * ticks_per_rev)
        self._dist_left += abs(v_left) * dt / 100   # m
        self._dist_right += abs(v_right) * dt / 100

        self.last_encoder = EncoderSample(
            rpm_left, rpm_right,
            self._ticks_left, self._ticks_right,
            self._dist_left, self._dist_right,
            now,
        )
        self.encoder_history.append(self.last_encoder)
        if len(self.encoder_history) > self._max_history:
            self.encoder_history.pop(0)
