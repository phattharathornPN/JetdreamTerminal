import subprocess
import os
import signal
from models.session import Session
from utils.logger import log


class RdpClient:
    def __init__(self, session: Session):
        self.session = session
        self._process = None

    def build_command(self, username: str, password: str) -> list[str]:
        cmd = [
            "xfreerdp",
            f"/v:{self.session.host}",
            f"/port:{self.session.port}",
            f"/w:{self.session.rdp_width}",
            f"/h:{self.session.rdp_height}",
            "/cert:ignore",
            "/auto-reconnect",
        ]
        if username:
            cmd.append(f"/u:{username}")
        if password:
            cmd.append(f"/p:{password}")
        return cmd

    def launch(self, username: str, password: str):
        if not self.session.host:
            log.error("RDP: no host configured")
            return
        if not username:
            log.error("RDP: username required")
            return
        if not password:
            log.error("RDP: password required")
            return

        cmd = self.build_command(username, password)
        log.info(f"RDP launching: xfreerdp /v:{self.session.host} /u:{username} ...")
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )
        except FileNotFoundError:
            log.error("xfreerdp not found. Install: sudo apt install freerdp2-x11")
        except Exception as e:
            log.error(f"RDP launch failed: {e}")

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
