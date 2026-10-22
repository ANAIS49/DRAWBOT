"""
panels/trajectory_panel.py
==========================
Panneau [5] : Visualisation de la trajectoire 2D du robot.

Utilise pyqtgraph pour afficher :
  - une grille (carreaux 1 cm + sous-graduations 1 mm) ;
  - la trajectoire historique (ligne fine bleu clair) ;
  - le tracé du stylo quand il est baissé (couleur configurable) ;
  - une trajectoire théorique en pointillés (preview de séquence) ;
  - un marqueur de position courante (cercle rouge clignotant) et
    un triangle d'orientation ;
  - une barre d'outils zoom / centrer / effacer / exporter PNG-SVG.

Les données sont lues à intervalles réguliers depuis le ``FakeDataGenerator``.
"""

import math
from typing import List, Tuple

import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters  # noqa: F401  (force le chargement des exporters)
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QColor, QPen, QPainter
from PyQt5.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from utils.fake_data import FakeDataGenerator
from utils.styles import COLORS


class TrajectoryPanel(QGroupBox):
    """Vue 2D de la trajectoire du robot."""

    def __init__(self, log_callback, fake: FakeDataGenerator,
                 manual_panel=None, parent=None) -> None:
        super().__init__("Trajectoire et dessin", parent)
        self._log = log_callback
        self._fake = fake
        self._manual = manual_panel  # pour connaître l'état du stylo

        # Historiques de points
        self._traj_points: List[Tuple[float, float]] = []   # toujours
        self._pen_segments: List[List[Tuple[float, float]]] = [[]]  # quand stylo baissé
        self._preview_points: List[Tuple[float, float]] = []

        self._pen_color = QColor(COLORS["primary"])
        self._pen_width = 2

        self._build_ui()
        self._setup_timer()

    # ------------------------------------------------------------------
    # Construction de l'UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # --- Barre d'outils ---
        toolbar = QHBoxLayout()
        for text, slot in [
            ("🔍+", self._zoom_in),
            ("🔍-", self._zoom_out),
            ("🎯 Centrer", self._center_on_robot),
            ("📐 Ajuster", self._fit_view),
            ("🗑 Effacer", self._clear_trajectory),
            ("💾 PNG", self._export_png),
            ("💾 SVG", self._export_svg),
        ]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            toolbar.addWidget(b)

        toolbar.addWidget(QLabel("Couleur :"))
        self.color_button = QPushButton()
        self.color_button.setFixedSize(28, 22)
        self._refresh_color_button()
        self.color_button.clicked.connect(self._pick_color)
        toolbar.addWidget(self.color_button)

        toolbar.addWidget(QLabel("Épaisseur :"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 5)
        self.width_spin.setValue(self._pen_width)
        self.width_spin.valueChanged.connect(self._on_width_changed)
        toolbar.addWidget(self.width_spin)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # --- Plot principal ---
        self.plot = pg.PlotWidget()
        self.plot.setBackground(COLORS["bg_console"])
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setAspectLocked(True)
        self.plot.setLabel("left", "Y (cm)")
        self.plot.setLabel("bottom", "X (cm)")
        self.plot.setRange(xRange=(-30, 30), yRange=(-30, 30))
        layout.addWidget(self.plot, 1)

        # Préparation des items graphiques
        self.curve_history = self.plot.plot(
            pen=pg.mkPen(QColor(74, 158, 255, 150), width=1)
        )
        self.curve_preview = self.plot.plot(
            pen=pg.mkPen(QColor(COLORS["text_dim"]), width=1, style=Qt.DashLine)
        )
        self._pen_curves = []

        # Marqueurs : départ (croix verte) et position courante
        self.start_marker = self.plot.plot(
            [0], [0],
            pen=None,
            symbol="x", symbolSize=12,
            symbolBrush=COLORS["success"], symbolPen=COLORS["success"],
        )
        self.robot_marker = self.plot.plot(
            [0], [0],
            pen=None,
            symbol="t", symbolSize=14,
            symbolBrush=COLORS["danger"], symbolPen="w",
        )
        self._blink_visible = True

        # --- Barre du bas (souris + légende) ---
        bottom = QHBoxLayout()
        self.scale_label = QLabel("Échelle : ⊢——⊣ 5 cm")
        self.scale_label.setProperty("role", "dim")
        bottom.addWidget(self.scale_label)
        bottom.addStretch()
        self.mouse_label = QLabel("Souris : X=-- cm, Y=-- cm")
        self.mouse_label.setProperty("role", "dim")
        bottom.addWidget(self.mouse_label)
        bottom.addStretch()
        legend = QLabel(
            f'<span style="color:{COLORS["primary"]};">▬</span> Trajectoire   '
            f'<span style="color:{COLORS["text_dim"]};">┄</span> Preview   '
            f'<span style="color:{COLORS["danger"]};">▲</span> Robot'
        )
        bottom.addWidget(legend)
        layout.addLayout(bottom)

        # Suivi de la souris dans le plot
        self.plot.scene().sigMouseMoved.connect(self._on_mouse_moved)

    # ------------------------------------------------------------------
    # Timer (rafraîchissement de la position et clignotement)
    # ------------------------------------------------------------------
    def _setup_timer(self) -> None:
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(100)
        self._update_timer.timeout.connect(self._on_tick)
        self._update_timer.start()

        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(500)
        self._blink_timer.timeout.connect(self._toggle_blink)
        self._blink_timer.start()

    def _on_tick(self) -> None:
        """Lit la pose et met à jour la trajectoire."""
        p = self._fake.pose
        # Évite les doublons exacts (économie CPU)
        if not self._traj_points or (
            abs(self._traj_points[-1][0] - p.x) > 1e-3
            or abs(self._traj_points[-1][1] - p.y) > 1e-3
        ):
            self._traj_points.append((p.x, p.y))
            if self._manual is not None and self._manual.is_pen_down():
                self._pen_segments[-1].append((p.x, p.y))
            else:
                # Démarrer un nouveau segment vide à la prochaine descente du stylo
                if self._pen_segments[-1]:
                    self._pen_segments.append([])
            self._refresh_curves()

        # Marqueur robot
        self.robot_marker.setData([p.x], [p.y])

    def _toggle_blink(self) -> None:
        """Fait clignoter le marqueur du robot."""
        self._blink_visible = not self._blink_visible
        self.robot_marker.setVisible(self._blink_visible)

    # ------------------------------------------------------------------
    # API publique : trajectoire de preview
    # ------------------------------------------------------------------
    def set_preview(self, points: List[Tuple[float, float]]) -> None:
        """Affiche une trajectoire théorique en pointillés gris."""
        self._preview_points = list(points)
        if points:
            xs = [pt[0] for pt in points]
            ys = [pt[1] for pt in points]
            self.curve_preview.setData(np.array(xs), np.array(ys))
        else:
            self.curve_preview.clear()

    def clear_preview(self) -> None:
        """Efface la trajectoire de preview."""
        self.set_preview([])

    # ------------------------------------------------------------------
    # Gestion des courbes
    # ------------------------------------------------------------------
    def _refresh_curves(self) -> None:
        """Rebuild les courbes historique + segments stylo."""
        if self._traj_points:
            xs = np.array([p[0] for p in self._traj_points])
            ys = np.array([p[1] for p in self._traj_points])
            self.curve_history.setData(xs, ys)

        # Met à jour les segments du stylo
        # Stratégie simple : on supprime les anciennes courbes et on les recrée.
        for c in self._pen_curves:
            self.plot.removeItem(c)
        self._pen_curves = []
        for seg in self._pen_segments:
            if len(seg) < 2:
                continue
            xs = np.array([p[0] for p in seg])
            ys = np.array([p[1] for p in seg])
            curve = self.plot.plot(
                xs, ys,
                pen=pg.mkPen(self._pen_color, width=self._pen_width)
            )
            self._pen_curves.append(curve)

    # ------------------------------------------------------------------
    # Callbacks toolbar
    # ------------------------------------------------------------------
    def _zoom_in(self) -> None:
        vb = self.plot.getViewBox()
        vb.scaleBy((0.7, 0.7))

    def _zoom_out(self) -> None:
        vb = self.plot.getViewBox()
        vb.scaleBy((1.4, 1.4))

    def _center_on_robot(self) -> None:
        p = self._fake.pose
        vb = self.plot.getViewBox()
        x_range, y_range = vb.viewRange()
        dx = (x_range[1] - x_range[0]) / 2
        dy = (y_range[1] - y_range[0]) / 2
        vb.setRange(xRange=(p.x - dx, p.x + dx),
                    yRange=(p.y - dy, p.y + dy), padding=0)

    def _fit_view(self) -> None:
        if not self._traj_points:
            self.plot.setRange(xRange=(-30, 30), yRange=(-30, 30))
            return
        xs = [p[0] for p in self._traj_points]
        ys = [p[1] for p in self._traj_points]
        margin = 5
        self.plot.setRange(
            xRange=(min(xs) - margin, max(xs) + margin),
            yRange=(min(ys) - margin, max(ys) + margin),
        )

    def _clear_trajectory(self) -> None:
        self._traj_points.clear()
        self._pen_segments = [[]]
        self.curve_history.clear()
        for c in self._pen_curves:
            self.plot.removeItem(c)
        self._pen_curves = []
        self._log("INFO", "Trajectoire effacée")

    def _export_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter en PNG", "trajectory.png", "Images PNG (*.png)"
        )
        if not path:
            return
        try:
            exporter = pg.exporters.ImageExporter(self.plot.plotItem)
            exporter.export(path)
            self._log("SUCCESS", f"Trajectoire exportée vers {path}")
        except Exception as err:  # pyqtgraph peut lever divers exceptions
            self._log("ERROR", f"Échec export PNG : {err}")

    def _export_svg(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter en SVG", "trajectory.svg", "Images SVG (*.svg)"
        )
        if not path:
            return
        try:
            exporter = pg.exporters.SVGExporter(self.plot.plotItem)
            exporter.export(path)
            self._log("SUCCESS", f"Trajectoire exportée vers {path}")
        except Exception as err:
            self._log("ERROR", f"Échec export SVG : {err}")

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(self._pen_color, self, "Couleur du tracé")
        if color.isValid():
            self._pen_color = color
            self._refresh_color_button()
            self._refresh_curves()

    def _refresh_color_button(self) -> None:
        self.color_button.setStyleSheet(
            f"background-color: {self._pen_color.name()}; border: 1px solid {COLORS['border']};"
        )

    def _on_width_changed(self, value: int) -> None:
        self._pen_width = value
        self._refresh_curves()

    def _on_mouse_moved(self, scene_pos) -> None:
        """Met à jour le label coordonnées souris en cm."""
        if not self.plot.sceneBoundingRect().contains(scene_pos):
            return
        vb = self.plot.getViewBox()
        view_pos = vb.mapSceneToView(scene_pos)
        self.mouse_label.setText(
            f"Souris : X={view_pos.x():+.1f} cm, Y={view_pos.y():+.1f} cm"
        )
