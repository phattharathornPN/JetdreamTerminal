import subprocess
import os
import signal
import shutil
import tempfile
from models.session import Session
from utils.logger import log


_OBFUSCATE_BIN = os.path.join(os.path.dirname(__file__), "vnc_obfuscate")


def _make_vnc_password(password: str) -> str:
    path = tempfile.mktemp(suffix=".vncpw")
    if os.path.isfile(_OBFUSCATE_BIN):
        try:
            result = subprocess.run(
                [_OBFUSCATE_BIN, password[:8]],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout:
                with open(path, "wb") as f:
                    f.write(result.stdout)
                return path
        except Exception:
            pass
    raw = password.encode("utf-8")[:8].ljust(8, b"\x00")
    with open(path, "wb") as f:
        f.write(raw)
    return path


def _find_vnc_viewer() -> str | None:
    for name in ("vncviewer", "remmina", "xtightvncviewer"):
        if shutil.which(name):
            return name
    return None


class VncClient:
    def __init__(self, session: Session):
        self.session = session
        self._process = None
        self._passwd_file = None

    def launch(self, password: str = ""):
        host = self.session.host
        port = self.session.vnc_port or 5901
        viewer = _find_vnc_viewer()

        if not viewer:
            log.error("No VNC viewer found. Install: sudo apt install tigervnc-viewer")
            return

        if viewer == "vncviewer":
            cmd = ["vncviewer"]
            if password:
                self._passwd_file = _make_vnc_password(password)
                cmd += ["-PasswordFile", self._passwd_file]
            cmd.append(f"{host}::{port}")
        elif viewer == "remmina":
            cmd = ["remmina", "-c", f"vnc://{host}:{port}"]
        elif viewer == "xtightvncviewer":
            cmd = ["xtightvncviewer", f"{host}::{port}"]
        else:
            return

        log.info(f"VNC launching: {viewer} {host}::{port}")
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )
        except FileNotFoundError:
            log.error(f"{viewer} not found. Install: sudo apt install tigervnc-viewer")
        except Exception as e:
            log.error(f"VNC launch failed: {e}")

    def is_running(self) -> bool:
        if self._process:
            return self._process.poll() is None
        return False

    def close(self):
        if self._process:
            try:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass
            self._process = None
        if self._passwd_file:
            try:
                os.unlink(self._passwd_file)
            except OSError:
                pass
            self._passwd_file = None
