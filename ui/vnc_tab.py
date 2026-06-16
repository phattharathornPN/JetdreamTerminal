from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from models.session import Session
from core.vnc_client import VncClient
from core.crypto import decrypt
from utils.logger import log


class VncTab(QWidget):
    closed = pyqtSignal(object)

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._client = VncClient(session)
        self._monitor = QTimer(self)
        self._monitor.timeout.connect(self._check_process)
        self._decrypted_password = ""
        if session.password_encrypted:
            try:
                self._decrypted_password = decrypt(session.password_encrypted)
            except Exception:
                pass
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QWidget()
        toolbar.setStyleSheet("background: #3b4252; padding: 4px;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(6, 4, 6, 4)
        toolbar_layout.setSpacing(6)

        toolbar_layout.addWidget(QLabel("Host:"))
        self._host_input = QLineEdit(self.session.host)
        self._host_input.setPlaceholderText("192.168.1.100")
        self._host_input.setMinimumWidth(150)
        toolbar_layout.addWidget(self._host_input)

        toolbar_layout.addWidget(QLabel("Port:"))
        self._port_input = QLineEdit(str(self.session.vnc_port or 5901))
        self._port_input.setFixedWidth(70)
        toolbar_layout.addWidget(self._port_input)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setFixedHeight(28)
        self._connect_btn.clicked.connect(self._on_connect)
        toolbar_layout.addWidget(self._connect_btn)

        toolbar_layout.addStretch()
        layout.addWidget(toolbar)

        self._status = QLabel("Ready")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet("color: #d8dee9; padding: 8px;")
        layout.addWidget(self._status)

        layout.addStretch()

    def _on_connect(self):
        host = self._host_input.text().strip()
        port_text = self._port_input.text().strip()

        if not host:
            self._status.setText("Host is required")
            return

        try:
            port = int(port_text)
        except ValueError:
            port = 5901

        self.session.host = host
        self.session.vnc_port = port

        password = ""
        if self.session.password_encrypted:
            try:
                password = decrypt(self.session.password_encrypted)
            except Exception:
                pass

        self._connect_btn.setEnabled(False)
        self._status.setText(f"Connecting to {host}::{port}...")
        self._client.launch(password)

        if self._client.is_running():
            self._status.setText(f"VNC connected: {host}::{port}")
            self._monitor.start(1000)
        else:
            self._status.setText(
                "Connection failed. Install: sudo apt install tigervnc-viewer"
            )
            self._connect_btn.setEnabled(True)

    def _check_process(self):
        if not self._client.is_running():
            self._monitor.stop()
            self._status.setText("VNC disconnected")
            self._connect_btn.setEnabled(True)

    def close_terminal(self):
        self._monitor.stop()
        self._client.close()
