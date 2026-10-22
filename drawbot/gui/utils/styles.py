"""
utils/styles.py
================
Feuilles de style QSS centralisées et palette de couleurs du Drawbot
Control Panel. Toutes les couleurs et tailles principales y sont définies
pour faciliter la maintenance du thème graphique.
"""

# ---------------------------------------------------------------------------
# Palette de couleurs (thème sombre "dark blue" professionnel)
# ---------------------------------------------------------------------------
COLORS = {
    "bg_window":     "#1e1e2e",
    "bg_panel":      "#2a2a3e",
    "bg_panel_alt":  "#32324a",
    "bg_console":    "#0f0f18",
    "text":          "#e0e0e0",
    "text_dim":      "#9090a0",
    "primary":       "#4a9eff",
    "success":       "#4ade80",
    "danger":        "#ef4444",
    "warning":       "#fbbf24",
    "border":        "#3a3a55",

    # Couleurs spécifiques au panneau console
    "log_info":      "#e0e0e0",
    "log_success":   "#4ade80",
    "log_warning":   "#fbbf24",
    "log_error":     "#ef4444",
    "log_debug":     "#888899",
    "log_tx":        "#22d3ee",
    "log_rx":        "#e879f9",
}


# ---------------------------------------------------------------------------
# Feuille de style globale
# ---------------------------------------------------------------------------
def get_global_stylesheet() -> str:
    """Retourne la feuille de style QSS globale appliquée à la QApplication."""
    return f"""
    /* === Fenêtre & widgets génériques === */
    QMainWindow, QWidget {{
        background-color: {COLORS["bg_window"]};
        color: {COLORS["text"]};
        font-family: "Segoe UI", "Roboto", "Helvetica Neue", sans-serif;
        font-size: 10pt;
    }}

    /* === QGroupBox (panneaux encadrés) === */
    QGroupBox {{
        background-color: {COLORS["bg_panel"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
        margin-top: 14px;
        padding: 8px 6px 6px 6px;
        font-weight: bold;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 6px;
        color: {COLORS["primary"]};
    }}

    /* === Boutons génériques === */
    QPushButton {{
        background-color: {COLORS["bg_panel_alt"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 6px;
        padding: 6px 12px;
    }}
    QPushButton:hover {{
        background-color: #3a3a55;
        border: 1px solid {COLORS["primary"]};
    }}
    QPushButton:pressed {{
        background-color: #1f1f30;
    }}
    QPushButton:disabled {{
        background-color: #25253a;
        color: {COLORS["text_dim"]};
        border: 1px solid #2a2a40;
    }}

    /* Variantes de boutons (via property "variant") */
    QPushButton[variant="primary"] {{
        background-color: {COLORS["primary"]};
        color: white;
        border: none;
        font-weight: bold;
    }}
    QPushButton[variant="primary"]:hover {{
        background-color: #6cb0ff;
    }}
    QPushButton[variant="success"] {{
        background-color: {COLORS["success"]};
        color: #0a3320;
        border: none;
        font-weight: bold;
    }}
    QPushButton[variant="success"]:hover {{
        background-color: #6ef0a0;
    }}
    QPushButton[variant="danger"] {{
        background-color: {COLORS["danger"]};
        color: white;
        border: none;
        font-weight: bold;
    }}
    QPushButton[variant="danger"]:hover {{
        background-color: #ff6060;
    }}
    QPushButton[variant="warning"] {{
        background-color: {COLORS["warning"]};
        color: #3a2800;
        border: none;
        font-weight: bold;
    }}
    QPushButton[variant="warning"]:hover {{
        background-color: #ffd45a;
    }}
    QPushButton[variant="emergency"] {{
        background-color: #d11515;
        color: white;
        border: 2px solid #ff6060;
        border-radius: 8px;
        font-weight: bold;
        font-size: 12pt;
    }}
    QPushButton[variant="emergency"]:hover {{
        background-color: #ff2020;
    }}

    /* === Labels === */
    QLabel {{
        color: {COLORS["text"]};
        background: transparent;
    }}
    QLabel[role="dim"] {{
        color: {COLORS["text_dim"]};
    }}
    QLabel[role="value"] {{
        font-family: "Consolas", "Menlo", "Courier New", monospace;
        font-size: 14pt;
        color: {COLORS["primary"]};
    }}
    QLabel[role="big-value"] {{
        font-family: "Consolas", "Menlo", "Courier New", monospace;
        font-size: 24pt;
        color: {COLORS["primary"]};
        font-weight: bold;
    }}

    /* === ComboBox === */
    QComboBox {{
        background-color: {COLORS["bg_panel_alt"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 4px;
        padding: 4px 8px;
        color: {COLORS["text"]};
    }}
    QComboBox:hover {{
        border: 1px solid {COLORS["primary"]};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 18px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {COLORS["bg_panel_alt"]};
        color: {COLORS["text"]};
        selection-background-color: {COLORS["primary"]};
        border: 1px solid {COLORS["border"]};
    }}

    /* === LineEdit, SpinBox === */
    QLineEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {COLORS["bg_panel_alt"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 4px;
        padding: 4px 8px;
        color: {COLORS["text"]};
        selection-background-color: {COLORS["primary"]};
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {COLORS["primary"]};
    }}

    /* === Sliders === */
    QSlider::groove:horizontal {{
        height: 6px;
        background: {COLORS["bg_panel_alt"]};
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {COLORS["primary"]};
        width: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    QSlider::handle:horizontal:hover {{
        background: #6cb0ff;
    }}
    QSlider::sub-page:horizontal {{
        background: {COLORS["primary"]};
        border-radius: 3px;
    }}

    /* === ProgressBar === */
    QProgressBar {{
        background-color: {COLORS["bg_panel_alt"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 4px;
        text-align: center;
        color: {COLORS["text"]};
    }}
    QProgressBar::chunk {{
        background-color: {COLORS["primary"]};
        border-radius: 3px;
    }}

    /* === Tabs === */
    QTabWidget::pane {{
        border: 1px solid {COLORS["border"]};
        background-color: {COLORS["bg_panel"]};
        border-radius: 6px;
    }}
    QTabBar::tab {{
        background-color: {COLORS["bg_panel_alt"]};
        color: {COLORS["text_dim"]};
        padding: 6px 12px;
        border: 1px solid {COLORS["border"]};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }}
    QTabBar::tab:selected {{
        background-color: {COLORS["bg_panel"]};
        color: {COLORS["primary"]};
        border-bottom: 2px solid {COLORS["primary"]};
    }}
    QTabBar::tab:hover {{
        color: {COLORS["text"]};
    }}

    /* === CheckBox & RadioButton === */
    QCheckBox, QRadioButton {{
        color: {COLORS["text"]};
        spacing: 6px;
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 14px;
        height: 14px;
    }}
    QCheckBox::indicator {{
        background-color: {COLORS["bg_panel_alt"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 3px;
    }}
    QCheckBox::indicator:checked {{
        background-color: {COLORS["primary"]};
        border: 1px solid {COLORS["primary"]};
    }}
    QRadioButton::indicator {{
        background-color: {COLORS["bg_panel_alt"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 7px;
    }}
    QRadioButton::indicator:checked {{
        background-color: {COLORS["primary"]};
        border: 3px solid {COLORS["bg_panel_alt"]};
    }}

    /* === TextEdit (console) === */
    QTextEdit {{
        background-color: {COLORS["bg_console"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 4px;
        font-family: "Consolas", "Menlo", "Courier New", monospace;
        font-size: 9pt;
    }}

    /* === Menus === */
    QMenuBar {{
        background-color: {COLORS["bg_panel"]};
        color: {COLORS["text"]};
        border-bottom: 1px solid {COLORS["border"]};
    }}
    QMenuBar::item:selected {{
        background-color: {COLORS["primary"]};
    }}
    QMenu {{
        background-color: {COLORS["bg_panel"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["border"]};
    }}
    QMenu::item:selected {{
        background-color: {COLORS["primary"]};
    }}

    /* === StatusBar === */
    QStatusBar {{
        background-color: {COLORS["bg_panel"]};
        color: {COLORS["text_dim"]};
        border-top: 1px solid {COLORS["border"]};
    }}

    /* === ScrollBar === */
    QScrollBar:vertical {{
        background: {COLORS["bg_panel"]};
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS["bg_panel_alt"]};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLORS["primary"]};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0;
    }}
    """
