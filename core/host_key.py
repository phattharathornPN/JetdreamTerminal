import subprocess
from pathlib import Path
from utils.config import KNOWN_HOSTS
from utils.logger import log


class HostKeyFetcher:
    def __init__(self):
        self._process = None

    def fetch(self, host: str, port: int = 22, legacy_mode: bool = False) -> dict | None:
        try:
            cmd = ["ssh-keyscan", "-p", str(port), host]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10,
            )

            lines = result.stdout.strip().split("\n")
            if not lines:
                return None

            keys = []
            for line in lines:
                if line.startswith("#"):
                    continue
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    keys.append({
                        "type": parts[1],
                        "key": parts[2],
                        "line": line,
                    })

            if not keys:
                return {"host": host, "port": port, "keys": [], "legacy": legacy_mode}

            return {"host": host, "port": port, "keys": keys}
        except Exception as e:
            log.error(f"HostKeyFetcher failed for {host}: {e}")
            return None

    def is_known(self, host: str, port: int = 22) -> bool:
        try:
            result = subprocess.run(
                ["ssh-keygen", "-F", f"[{host}]:{port}" if port != 22 else host],
                capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def accept_key(self, host: str, port: int, key_line: str):
        KNOWN_HOSTS.parent.mkdir(parents=True, exist_ok=True)
        with open(KNOWN_HOSTS, "a") as f:
            f.write(key_line + "\n")
        log.info(f"Accepted host key for {host}:{port}")
