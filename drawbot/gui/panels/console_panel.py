"""
panels/console_panel.py
=======================
Panneau [6] : Console & journal d'évènements.

Affiche les logs colorés selon le niveau (INFO, SUCCESS, WARNING, ERROR,
DEBUG, TX, RX), avec filtres par niveau, recherche textuelle, export et
mise en pause de l'auto-scroll.

L'API publique principale est ``ConsolePanel.log(level, message)`` : tous
les autres panneaux passent par cette méthode pour publier des évènements.
"""

from datetime import datetime
from typing import List, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor, QFont
from PyQt5.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from utils.styles import COLORS


# Couleurs HTML par niveau (utilisées pour formater chaque ligne en HTML).
LEVEL_COLORS = {
    "INFO":    COLORS["log_info"],
    "SUCCESS": COLORS["log_success"],
    "WARNING": COLORS["log_warning"],
    "ERROR":   COLORS["log_error"],
    "DEBUG":   COLORS["log_debug"],
    "TX":      COLORS["log_tx"],
    "RX":      COLORS["log_rx"],
}


class ConsolePanel(QGroupBox):
    """Console interactive d'affichage des logs."""

    def __init__(self, parent=None) -> None:
        super().__init__("Console & journal", parent)

        # Stockage des entrées brutes pour pouvoir refiltrer dynamiquement.
        # Chaque entrée : (timestamp_str, level, message)
        self._entries: List[Tuple[str, str, str]] = []

        # Niveaux activés (cochés)
        self._enabled_levels = {
            "INFO": True, "SUCCESS": True, "WARNING": True,
            "ERROR": True, "DEBUG": False, "TX": True, "RX": True,
        }
        self._search_text = ""
        self._auto_scroll = True

        # Compteurs pour la barre de stats
        self._error_count = 0
        self._warning_count = 0

        self._build_ui()

    # ------------------------------------------------------------------
    # Construction de l'UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """Construit la disposition complète du panneau."""
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # --- Barre de filtres par niveau ---
        filters_row = QHBoxLayout()
        filters_row.addWidget(QLabel("Filtres :"))
        self._level_checkboxes = {}
        for level in ("INFO", "SUCCESS", "WARNING", "ERROR", "DEBUG", "TX", "RX"):
            cb = QCheckBox(level)
            cb.setChecked(self._enabled_levels[level])
            cb.stateChanged.connect(self._on_filter_changed)
            self._level_checkboxes[level] = cb
            filters_row.addWidget(cb)
        filters_row.addStretch()
        layout.addLayout(filters_row)

        # --- Barre d'outils (recherche + boutons) ---
        toolbar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Rechercher dans les logs...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.search_edit, 1)

        self.clear_button = QPushButton("🗑 Effacer")
        self.clear_button.clicked.connect(self.clear_logs)
        toolbar.addWidget(self.clear_button)

        self.export_button = QPushButton("💾 Exporter (.txt)")
        self.export_button.clicked.connect(self._export_logs)
        toolbar.addWidget(self.export_button)

        self.pause_button = QPushButton("⏸ Pause auto-scroll")
        self.pause_button.setCheckable(True)
        self.pause_button.toggled.connect(self._on_pause_toggled)
        toolbar.addWidget(self.pause_button)

        layout.addLayout(toolbar)

        # --- Zone de texte principale ---
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setFont(QFont("Consolas", 9))
        layout.addWidget(self.text_area, 1)

        # --- Statistiques en bas ---
        self.stats_label = QLabel("Lignes : 0 | Erreurs : 0 | Avertissements : 0")
        self.stats_label.setProperty("role", "dim")
        layout.addWidget(self.stats_label)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------
    def log(self, level: str, message: str) -> None:
        """
        Ajoute une ligne de log.

        :param level: niveau (INFO, SUCCESS, WARNING, ERROR, DEBUG, TX, RX)
        :param message: contenu textuel à afficher
        """
        level = level.upper()
        if level not in LEVEL_COLORS:
            level = "INFO"

        timestamp = datetime.now().strftime("%H:%M:%S")
        self._entries.append((timestamp, level, message))

        if level == "ERROR":
            self._error_count += 1
        elif level == "WARNING":
            self._warning_count += 1

        if self._matches_filter(level, message):
            self._append_html_line(timestamp, level, message)

        self._update_stats()

    def clear_logs(self) -> None:
        """Vide complètement la console et réinitialise les compteurs."""
        self._entries.clear()
        self._error_count = 0
        self._warning_count = 0
        self.text_area.clear()
        self._update_stats()

    # ------------------------------------------------------------------
    # Filtrage / recherche
    # ------------------------------------------------------------------
    def _matches_filter(self, level: str, message: str) -> bool:
        """Indique si une entrée passe les filtres niveau + recherche."""
        if not self._enabled_levels.get(level, False):
            return False
        if self._search_text and self._search_text.lower() not in message.lower():
            return False
        return True

    def _on_filter_changed(self) -> None:
        """Réagit au changement d'état d'une case à cocher de niveau."""
        for level, cb in self._level_checkboxes.items():
            self._enabled_levels[level] = cb.isChecked()
        self._refresh_view()

    def _on_search_changed(self, text: str) -> None:
        """Réagit à la frappe dans le champ de recherche."""
        self._search_text = text
        self._refresh_view()

    def _refresh_view(self) -> None:
        """Reconstruit l'affichage à partir du tampon d'entrées brutes."""
        self.text_area.clear()
        for ts, level, msg in self._entries:
            if self._matches_filter(level, msg):
                self._append_html_line(ts, level, msg)

    # ------------------------------------------------------------------
    # Auto-scroll
    # ------------------------------------------------------------------
    def _on_pause_toggled(self, checked: bool) -> None:
        """Bascule la pause d'auto-scroll et met à jour le libellé."""
        self._auto_scroll = not checked
        self.pause_button.setText(
            "▶ Reprendre" if checked else "⏸ Pause auto-scroll"
        )

    def _append_html_line(self, ts: str, level: str, message: str) -> None:
        """Insère une ligne formatée HTML dans la zone de texte."""
        color = LEVEL_COLORS.get(level, COLORS["text"])
        # Mise en forme : timestamp gris, niveau coloré sur 7 caractères, message
        html = (
            f'<span style="color:{COLORS["text_dim"]};">[{ts}]</span> '
            f'<span style="color:{color}; font-weight:bold;">[{level:<7}]</span> '
            f'<span style="color:{color};">{self._escape(message)}</span>'
        )
        self.text_area.append(html)
        if self._auto_scroll:
            self.text_area.moveCursor(QTextCursor.End)

    @staticmethod
    def _escape(text: str) -> str:
        """Échappe les caractères HTML spéciaux pour éviter toute injection."""
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )

    # ------------------------------------------------------------------
    # Stats & export
    # ------------------------------------------------------------------
    def _update_stats(self) -> None:
        """Met à jour la barre de statistiques en bas."""
        self.stats_label.setText(
            f"Lignes : {len(self._entries)} | "
            f"Erreurs : {self._error_count} | "
            f"Avertissements : {self._warning_count}"
        )

    def _export_logs(self) -> None:
        """Exporte les logs courants dans un fichier texte choisi par l'utilisateur."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter les logs", "drawbot_logs.txt",
            "Fichiers texte (*.txt);;Tous les fichiers (*)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                for ts, level, msg in self._entries:
                    fh.write(f"[{ts}] [{level:<7}] {msg}\n")
            self.log("SUCCESS", f"Logs exportés vers {path}")
        except OSError as err:
            self.log("ERROR", f"Échec de l'export : {err}")
