import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal
from core.host_key import HostKeyFetcher
from utils.logger import log


class HostKeyDialog(QWidget):
    accepted = pyqtSignal()
    rejected = pyqtSignal()

    def __init__(self, host: str, port: int, host_info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Host Key Verification")
        self.setMinimumWidth(500)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.host = host
        self.port = port
        self.host_info = host_info
        self._setup_ui()
        self._center_on_parent()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        banner = QLabel("⚠️ New Host Key")
        banner.setStyleSheet("color: #ebcb8b; font-size: 16px; font-weight: bold; padding: 8px;")
        layout.addWidget(banner)

        info = QLabel(
            f"The authenticity of host '{self.host}:{self.port}' can't be established.\n"
            f"Please verify the fingerprint below before accepting."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        keys = self.host_info.get("keys", [])
        if keys:
            keys_text = ""
            for k in keys:
                fp = k.get("fingerprint", "")
                keys_text += f"  {k['type']} {fp}\n"
        elif self.host_info.get("legacy"):
            keys_text = (
                "Host is reachable but ssh-keyscan could not retrieve the key.\n"
                "This is common with older Cisco/network devices.\n"
                "You can still connect if you trust this host."
            )
        else:
            keys_text = "No host key received from server."

        self._keys_display = QTextEdit()
        self._keys_display.setPlainText(keys_text)
        self._keys_display.setReadOnly(True)
        self._keys_display.setMaximumHeight(100)
        self._keys_display.setStyleSheet("font-family: monospace; font-size: 12px;")
        layout.addWidget(self._keys_display)

        btn_layout = QHBoxLayout()
        self._accept_btn = QPushButton("Accept and Save")
        self._accept_btn.clicked.connect(self._on_accept)
        self._reject_btn = QPushButton("Reject")
        self._reject_btn.clicked.connect(self._on_reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self._reject_btn)
        btn_layout.addWidget(self._accept_btn)
        layout.addLayout(btn_layout)

    def _on_accept(self):
        keys = self.host_info.get("keys", [])
        if keys:
            fetcher = HostKeyFetcher()
            for k in keys:
                fetcher.accept_key(self.host, self.port, k["line"])
        self.accepted.emit()
        self.close()

    def _on_reject(self):
        self.rejected.emit()
        self.close()

    def _center_on_parent(self):
        parent = self.parent()
        if parent:
            pw, ph = parent.width(), parent.height()
            px, py = parent.x(), parent.y()
            sw, sh = self.width(), self.height()
            self.move(px + (pw - sw) // 2, py + (ph - sh) // 2)


class ChangedKeyDialog(QWidget):
    accepted = pyqtSignal()
    rejected = pyqtSignal()

    def __init__(self, host: str, port: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Host Key Changed!")
        self.setMinimumWidth(500)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.host = host
        self.port = port
        self._setup_ui()
        self._center_on_parent()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        banner = QLabel("🚨 WARNING: Host Key Changed!")
        banner.setStyleSheet(
            "color: #bf616a; font-size: 16px; font-weight: bold; "
            "background-color: #3b2020; padding: 12px; border-radius: 4px;"
        )
        layout.addWidget(banner)

        info = QLabel(
            f"The host key for '{self.host}:{self.port}' has changed!\n"
            f"This could indicate a man-in-the-middle attack.\n"
            f"The connection has been refused."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        btn_layout = QHBoxLayout()
        self._abort_btn = QPushButton("Abort (Recommended)")
        self._abort_btn.clicked.connect(self._on_abort)
        btn_layout.addStretch()
        btn_layout.addWidget(self._abort_btn)
        layout.addLayout(btn_layout)

    def _on_abort(self):
        self.rejected.emit()
        self.close()

    def _center_on_parent(self):
        parent = self.parent()
        if parent:
            pw, ph = parent.width(), parent.height()
            px, py = parent.x(), parent.y()
            sw, sh = self.width(), self.height()
            self.move(px + (pw - sw) // 2, py + (ph - sh) // 2)
