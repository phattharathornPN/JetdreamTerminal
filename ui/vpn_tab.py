import subprocess
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSplitter,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from models.session import Session
from ui.terminal_widget import TerminalWidget
from core.pty_manager import PtyManager
from core.crypto import decrypt
from utils.logger import log


class VpnTab(QWidget):
    closed = pyqtSignal(object)

    def __init__(self, session: Session = None, parent=None):
        super().__init__(parent)
        self.session = session
        self._pty = PtyManager(self)
        self._term = TerminalWidget(self)
        self._term.set_pty(self._pty)
        self._overlay = None
        self._connected = False
        self._setup_ui()
        self._pty.process_exited.connect(self._on_exit)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        row1 = QHBoxLayout()
        row1.setContentsMargins(6, 4, 6, 2)
        row1.setSpacing(6)

        row1.addWidget(QLabel("Host:"))
        self._host = QLineEdit()
        self._host.setPlaceholderText("vpn.example.com")
        if self.session:
            self._host.setText(self.session.host)
        row1.addWidget(self._host)

        row1.addWidget(QLabel("Port:"))
        self._port = QLineEdit("443")
        self._port.setFixedWidth(60)
        if self.session:
            self._port.setText(str(self.session.port))
        row1.addWidget(self._port)

        row1.addWidget(QLabel("User:"))
        self._user = QLineEdit()
        self._user.setPlaceholderText("username")
        if self.session:
            self._user.setText(self.session.username)
        row1.addWidget(self._user)

        row1.addStretch()

        self._connect_btn = QPushButton("🔌 Connect")
        self._connect_btn.setFixedHeight(28)
        self._connect_btn.clicked.connect(self._toggle_connect)
        row1.addWidget(self._connect_btn)

        row2 = QHBoxLayout()
        row2.setContentsMargins(6, 2, 6, 4)
        row2.setSpacing(6)

        row2.addWidget(QLabel("Realm:"))
        self._realm = QLineEdit()
        self._realm.setPlaceholderText("(optional)")
        self._realm.setFixedWidth(150)
        if self.session:
            self._realm.setText(self.session.vpn_realm)
        row2.addWidget(self._realm)

        row2.addWidget(QLabel("Trusted cert:"))
        self._trusted_cert = QLineEdit()
        self._trusted_cert.setPlaceholderText("sha256 hash from error message")
        if self.session:
            self._trusted_cert.setText(self.session.vpn_trusted_cert)
        row2.addWidget(self._trusted_cert)

        row2.addStretch()

        row2.addStretch()

        toolbar = QWidget()
        toolbar_layout = QVBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(0)
        toolbar_layout.addLayout(row1)
        toolbar_layout.addLayout(row2)
        toolbar.setStyleSheet("background: #3b4252;")
        layout.addWidget(toolbar)

        self._splitter = QSplitter(Qt.Orientation.Vertical)
        self._splitter.addWidget(self._term)
        layout.addWidget(self._splitter)

    def _toggle_connect(self):
        if self._connected:
            self._disconnect_vpn()
        else:
            self._connect_vpn()

    def _connect_vpn(self):
        host = self._host.text().strip()
        port = self._port.text().strip()
        user = self._user.text().strip()
        realm = self._realm.text().strip()
        trusted = self._trusted_cert.text().strip()

        if not host:
            self._show_overlay("Enter VPN host")
            return

        cmd = [
            "sudo", "-S", "openfortivpn",
            f"{host}:{port}",
        ]
        if user:
            cmd += ["-u", user]
        if realm:
            cmd += ["-r", realm]
        if trusted:
            cmd += ["--trusted-cert", trusted]

        log.info(f"VPN connecting: {host}:{port}...")
        self._pty.launch(cmd)
        self._connected = True
        self._connect_btn.setText("🔴 Disconnect")
        self._connect_btn.setStyleSheet("background: #bf616a; color: white;")
        QTimer.singleShot(100, self._term.setFocus)

    def _disconnect_vpn(self):
        if self._connected and self._pty.is_running():
            self._pty.write(b"\x03")
            QTimer.singleShot(500, self._force_disconnect)
        else:
            self._force_disconnect()

    def _force_disconnect(self):
        if self._pty.is_running():
            self._pty._cleanup()
        self._connected = False
        self._connect_btn.setText("🔌 Connect")
        self._connect_btn.setStyleSheet("")

    def _on_exit(self, code: int):
        self._connected = False
        self._connect_btn.setText("🔌 Connect")
        self._connect_btn.setStyleSheet("")
        if self.isVisible():
            log.info(f"VPN process exited: {code}")

    def _show_overlay(self, msg: str):
        if self._overlay:
            self._overlay.deleteLater()
        self._overlay = QLabel(msg, self._term)
        self._overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay.setStyleSheet(
            "background-color: rgba(46, 52, 64, 200); color: #d8dee9; "
            "font-size: 14px; padding: 20px; border-radius: 8px;"
        )
        tw = self._term.width()
        th = self._term.height()
        if tw > 0 and th > 0:
            self._overlay.setGeometry(tw // 4, th // 3, tw // 2, 60)
        self._overlay.show()

    def close_terminal(self):
        if self._pty.is_running():
            self._pty._cleanup()
        if self._pty:
            try:
                self._pty.data_received.disconnect()
                self._pty.process_exited.disconnect()
            except Exception:
                pass
