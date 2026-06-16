import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from utils.db import init_db
from utils.logger import log
from ui.main_window import MainWindow
from ui.theme import load_saved_theme

ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.svg")


def main():
    init_db()
    load_saved_theme()
    log.info("JetdreamTerminal starting...")

    app = QApplication(sys.argv)
    app.setApplicationName("JetdreamTerminal")

    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    font = QFont("JetBrains Mono", 13)
    font.setStyleHint(QFont.StyleHint.Monospace)
    app.setFont(font)

    window = MainWindow()
    window.show()

    log.info("JetdreamTerminal ready")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
