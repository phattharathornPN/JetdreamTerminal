from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from models.session import Session
from ui.sftp_panel import SftpPanel
from utils.logger import log


class SftpTab(QWidget):
    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._panel = SftpPanel(session, self)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._panel.connect_sftp()

        layout.addWidget(self._panel)

    def disconnect(self):
        if self._panel:
            self._panel.disconnect()
