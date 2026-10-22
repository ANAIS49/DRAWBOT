"""
main.py
========
Point d'entrée du Drawbot Control Panel.

Crée la QApplication, applique le thème sombre global, instancie la
fenêtre principale et lance la boucle d'évènements.

Lancement :
    python main.py
"""

import sys

from PyQt5.QtWidgets import QApplication

from main_window import MainWindow
from utils.styles import get_global_stylesheet


def main() -> int:
    """Démarre l'application Qt et retourne son code de sortie."""
    app = QApplication(sys.argv)
    app.setApplicationName("Drawbot Control Panel")
    app.setOrganizationName("Drawbot")
    app.setStyleSheet(get_global_stylesheet())

    window = MainWindow()
    window.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
