from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSplitter
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from models.session import Session, SessionType, AuthType
from core.pty_manager import PtyManager
from core.ssh_client import build_ssh_command
from core.host_key import HostKeyFetcher
from core.crypto import decrypt
from ui.terminal_widget import TerminalWidget
from ui.host_key_dialog import HostKeyDialog, ChangedKeyDialog
from utils.logger import log


class SSHTab(QWidget):
    closed = pyqtSignal(object)

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._pty = PtyManager(self)
        self._term = TerminalWidget(self)
        self._term.set_pty(self._pty)
        self._overlay = None
        self._connecting = False
        self._sftp_panel = None
        self._sftp_visible = False
        self._reconnect_count = 0
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.timeout.connect(self._do_reconnect)
        self._setup_ui()
        self._pty.process_exited.connect(self._on_exit)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 2, 4, 2)
        toolbar.setSpacing(4)

        self._sftp_btn = QPushButton("📁 SFTP")
        self._sftp_btn.setFixedHeight(26)
        self._sftp_btn.setCheckable(True)
        self._sftp_btn.clicked.connect(self._toggle_sftp)
        toolbar.addWidget(self._sftp_btn)

        toolbar.addStretch()

        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar)
        toolbar_widget.setFixedHeight(32)
        toolbar_widget.setStyleSheet("background: #3b4252;")
        layout.addWidget(toolbar_widget)

        self._splitter = QSplitter(Qt.Orientation.Vertical)
        self._splitter.addWidget(self._term)
        layout.addWidget(self._splitter)

    def _toggle_sftp(self):
        if self._sftp_visible:
            if self._sftp_panel:
                self._sftp_panel.hide()
            self._sftp_visible = False
            self._sftp_btn.setChecked(False)
        else:
            if not self._sftp_panel:
                from ui.sftp_panel import SftpPanel
                self._sftp_panel = SftpPanel(self.session, self)
                self._splitter.addWidget(self._sftp_panel)
                self._sftp_panel.connect_sftp()
            self._sftp_panel.show()
            self._sftp_visible = True
            self._sftp_btn.setChecked(True)
            sizes = self._splitter.sizes()
            if sizes[0] > 100:
                h = sizes[0] + sizes[1] if len(sizes) > 1 else sizes[0]
                self._splitter.setSizes([h * 6 // 10, h * 4 // 10])

    def showEvent(self, event):
        super().showEvent(event)
        if not self._pty.is_running() and not self._connecting:
            QTimer.singleShot(100, self._start_connection)

    def _start_connection(self):
        if self._connecting:
            return
        self._connecting = True

        if not self.session.host:
            self._show_overlay("No host configured")
            return

        host_key = HostKeyFetcher()
        if not host_key.is_known(self.session.host, self.session.port):
            info = host_key.fetch(self.session.host, self.session.port, self.session.legacy_mode)
            if info:
                dlg = HostKeyDialog(
                    self.session.host, self.session.port, info, self
                )
                dlg.accepted.connect(self._do_connect)
                dlg.rejected.connect(lambda: self._show_overlay("Connection refused"))
                dlg.show()
                return
            else:
                if self.session.legacy_mode:
                    log.info(f"ssh-keyscan failed for legacy host {self.session.host}, connecting anyway")
                    self._do_connect()
                    return
                self._show_overlay(f"Host unreachable: {self.session.host}")
                return
        self._do_connect()

    def _do_connect(self):
        password = ""
        if self.session.auth_type in (AuthType.PASSWORD, AuthType.KEY_WITH_PASSWORD):
            if self.session.password_encrypted:
                try:
                    password = decrypt(self.session.password_encrypted)
                except Exception:
                    pass

        cmd, env = build_ssh_command(self.session, password)
        log.info(f"Connecting: {' '.join(cmd[:6])}...")
        self._pty.launch(cmd, env if env else None)
        self._connecting = False
        self._term.setFocus()

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

    def _on_exit(self, code: int):
        if not self.isVisible():
            return
        if code != 0 and self._reconnect_count < 3:
            self._reconnect_count += 1
            delay = min(3000, 1000 * self._reconnect_count)
            self._show_overlay(f"Reconnecting in {delay // 1000}s... (attempt {self._reconnect_count}/3)")
            self._reconnect_timer.start(delay)
        else:
            self._show_overlay(f"Connection closed (exit code: {code})")

    def _do_reconnect(self):
        self._reconnect_timer.stop()
        self._connecting = False
        if self._overlay:
            self._overlay.deleteLater()
            self._overlay = None
        self._pty = PtyManager(self)
        self._term.set_pty(self._pty)
        self._pty.process_exited.connect(self._on_exit)
        self._start_connection()

    def close_terminal(self):
        if hasattr(self.session, 'auto_save') and self.session.auto_save:
            self._term.auto_save_output(self.session.name)
        if self._sftp_panel:
            self._sftp_panel.disconnect()
        if self._pty:
            self._pty.data_received.disconnect()
            self._pty.process_exited.disconnect()
        if self._pty and self._pty.is_running():
            self._pty._cleanup()
