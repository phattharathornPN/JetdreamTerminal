from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from models.session import Session
from core.rdp_client import RdpClient
from core.crypto import decrypt
from utils.logger import log


class RdpTab(QWidget):
    closed = pyqtSignal(object)

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._client = RdpClient(session)
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

        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)

        form_layout = QHBoxLayout()
        form_layout.addStretch()

        user_label = QLabel("Username:")
        self._user_input = QLineEdit(self.session.username)
        self._user_input.setPlaceholderText("Administrator")
        self._user_input.setMinimumWidth(200)

        pass_label = QLabel("Password:")
        self._pass_input = QLineEdit()
        self._pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass_input.setPlaceholderText("Enter password")
        self._pass_input.setMinimumWidth(200)
        if self._decrypted_password:
            self._pass_input.setText(self._decrypted_password)
        self._pass_input.returnPressed.connect(self._on_connect)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.clicked.connect(self._on_connect)

        form_layout.addWidget(user_label)
        form_layout.addWidget(self._user_input)
        form_layout.addWidget(pass_label)
        form_layout.addWidget(self._pass_input)
        form_layout.addWidget(self._connect_btn)
        form_layout.addStretch()
        layout.addLayout(form_layout)

        layout.addStretch()

    def _on_connect(self):
        username = self._user_input.text().strip()
        password = self._pass_input.text()

        if not username:
            self._status.setText("Username is required")
            return
        if not password:
            self._status.setText("Password is required")
            return

        self._connect_btn.setEnabled(False)
        self._status.setText(f"Connecting to {self.session.host}...")
        self._client.launch(username, password)

        if self._client.is_running():
            self._status.setText(f"RDP connected: {self.session.host}")
            self._monitor.start(1000)
        else:
            self._status.setText(
                "Connection failed. Check host/credentials.\n"
                "Or install: sudo apt install freerdp2-x11"
            )
            self._connect_btn.setEnabled(True)

    def _check_process(self):
        if not self._client.is_running():
            self._monitor.stop()
            self._status.setText("RDP disconnected")
            self._connect_btn.setEnabled(True)

    def close_rdp(self):
        self._monitor.stop()
        self._client.close()
