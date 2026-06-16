from models.session import Session
from core.ssh_client import build_telnet_command
from core.pty_manager import PtyManager
from ui.terminal_widget import TerminalWidget
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal, QTimer
from utils.logger import log


class TelnetTab(QWidget):
    closed = pyqtSignal(object)

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._pty = PtyManager(self)
        self._term = TerminalWidget(self)
        self._term.set_pty(self._pty)
        self._connecting = False
        self._reconnect_count = 0
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.timeout.connect(self._do_reconnect)
        self._setup_ui()
        self._pty.process_exited.connect(self._on_exit)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._term)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._pty.is_running() and not self._connecting:
            self._connecting = True
            QTimer.singleShot(100, self._start_telnet)

    def _start_telnet(self):
        cmd = build_telnet_command(self.session)
        log.info(f"Telnet connecting: {' '.join(cmd)}")
        self._pty.launch(cmd)
        self._connecting = False
        QTimer.singleShot(100, self._term.setFocus)

    def _on_exit(self, code: int):
        log.info(f"Telnet session exited: {code}")
        if code != 0 and self._reconnect_count < 3 and self.isVisible():
            self._reconnect_count += 1
            delay = min(3000, 1000 * self._reconnect_count)
            log.info(f"Telnet reconnecting in {delay}ms (attempt {self._reconnect_count}/3)")
            self._reconnect_timer.start(delay)

    def _do_reconnect(self):
        self._reconnect_timer.stop()
        self._connecting = False
        self._pty = PtyManager(self)
        self._term.set_pty(self._pty)
        self._pty.process_exited.connect(self._on_exit)
        self._start_telnet()

    def close_terminal(self):
        if hasattr(self.session, 'auto_save') and self.session.auto_save:
            self._term.auto_save_output(self.session.name)
        if self._pty:
            self._pty.data_received.disconnect()
            self._pty.process_exited.disconnect()
        if self._pty and self._pty.is_running():
            self._pty._cleanup()
