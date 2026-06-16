import os
import fcntl
import struct
import termios
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from utils.logger import log


class PtyManager(QObject):
    data_received = pyqtSignal(bytes)
    process_exited = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.master_fd: int = -1
        self._notifier = None
        self._pid: int = 0
        self._cols: int = 80
        self._rows: int = 24

    def launch(self, cmd: list[str], env: dict | None = None):
        import pty

        master_fd, slave_fd = pty.openpty()

        self._pid = os.fork()
        if self._pid == 0:
            os.close(master_fd)
            os.setsid()
            try:
                fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
            except OSError:
                pass
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)
            if slave_fd > 2:
                os.close(slave_fd)
            use_env = os.environ.copy()
            use_env.setdefault("TERM", "xterm-256color")
            if env:
                use_env.update(env)
            os.execvpe(cmd[0], cmd, use_env)
        else:
            os.close(slave_fd)
            self.master_fd = master_fd
            self._set_winsize(self._cols, self._rows)
            log.info(f"PTY launched: pid={self._pid}, fd={self.master_fd}")
            self._start_read()

    def _start_read(self):
        from PyQt6.QtCore import QSocketNotifier

        if self.master_fd < 0:
            return

        self._notifier = QSocketNotifier(
            self.master_fd, QSocketNotifier.Type.Read, self
        )
        self._notifier.activated.connect(self._on_ready_read)

    def _on_ready_read(self):
        if self.master_fd < 0:
            return
        try:
            data = os.read(self.master_fd, 65536)
            if data:
                self.data_received.emit(data)
            else:
                log.info("PTY EOF received")
                self._cleanup()
        except OSError as e:
            log.error(f"PTY read error: {e}")
            self._cleanup()

    def write(self, data: bytes):
        if self.master_fd >= 0:
            try:
                os.write(self.master_fd, data)
            except OSError:
                pass

    def resize(self, cols: int, rows: int):
        self._cols = cols
        self._rows = rows
        self._set_winsize(cols, rows)

    def _set_winsize(self, cols: int, rows: int):
        if self.master_fd >= 0:
            try:
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
            except OSError:
                pass

    def _cleanup(self):
        exit_code = 0
        if self._notifier:
            self._notifier.setEnabled(False)
            self._notifier.deleteLater()
            self._notifier = None
        if self.master_fd >= 0:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = -1
        if self._pid > 0:
            try:
                _, status = os.waitpid(self._pid, 0)
                exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
            except ChildProcessError:
                pass
            self._pid = 0
        self.process_exited.emit(exit_code)

    def is_running(self) -> bool:
        return self.master_fd >= 0
