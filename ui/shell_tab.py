import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal, QTimer
from models.session import Session, SessionType
from core.pty_manager import PtyManager
from ui.terminal_widget import TerminalWidget
from utils.logger import log


class ShellTab(QWidget):
    closed = pyqtSignal(object)

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._pty = PtyManager(self)
        self._term = TerminalWidget(self)
        self._term.set_pty(self._pty)
        self._connecting = False
        self._setup_ui()
        self._pty.process_exited.connect(self._on_exit)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 2, 4, 2)
        toolbar.setSpacing(4)

        self._shell_label = QLabel("")
        self._shell_label.setStyleSheet("color: #a5adba; font-size: 11px;")
        toolbar.addWidget(self._shell_label)

        toolbar.addStretch()

        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(26)
        save_btn.clicked.connect(self._term._save_output)
        toolbar.addWidget(save_btn)

        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar)
        toolbar_widget.setFixedHeight(28)
        toolbar_widget.setStyleSheet("background: #3b4252;")
        layout.addWidget(toolbar_widget)

        layout.addWidget(self._term)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._pty.is_running() and not self._connecting:
            self._connecting = True
            QTimer.singleShot(100, self._start_shell)

    def _start_shell(self):
        shell = os.environ.get("SHELL", "/bin/bash")
        self._shell_label.setText(f"Shell: {shell}")
        log.info(f"Shell launching: {shell}")
        self._pty.launch([shell], os.environ.copy())
        self._connecting = False
        self._term.setFocus()

    def _on_exit(self, code: int):
        log.info(f"Shell exited: {code}")

    def close_terminal(self):
        if self._pty:
            self._pty.data_received.disconnect()
            self._pty.process_exited.disconnect()
        if self._pty and self._pty.is_running():
            self._pty._cleanup()
