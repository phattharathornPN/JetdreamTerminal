import paramiko
import os
import socket
from models.session import Session, AuthType
from core.crypto import decrypt
from core.ssh_client import _is_windows_host
from utils.logger import log


class SftpBrowser:
    def __init__(self, session: Session):
        self.session = session
        self._client: paramiko.SSHClient | None = None
        self._transport: paramiko.Transport | None = None
        self._sftp: paramiko.SFTPClient | None = None

    @property
    def connected(self) -> bool:
        return self._sftp is not None

    def _load_key(self, key_path: str, password: str = ""):
        if not key_path or not os.path.exists(key_path):
            return None
        try:
            return paramiko.Ed25519Key.from_private_key_file(key_path, password=password or None)
        except Exception:
            pass
        try:
            return paramiko.RSAKey.from_private_key_file(key_path, password=password or None)
        except Exception:
            pass
        try:
            return paramiko.ECDSAKey.from_private_key_file(key_path, password=password or None)
        except Exception:
            pass
        try:
            return paramiko.DSSKey.from_private_key_file(key_path, password=password or None)
        except Exception:
            pass
        return None

    def connect(self, password: str = ""):
        self.disconnect()
        host = self.session.host
        port = self.session.port

        log.info(f"SFTP connecting: {self.session.username}@{host}:{port}")

        try:
            sock = socket.create_connection((host, port), timeout=15)
        except Exception as e:
            raise ConnectionError(f"Cannot reach {host}:{port} — {e}")

        try:
            self._transport = paramiko.Transport(sock)
            self._transport.local_version = "SSH-2.0-OpenSSH_8.9"

            pkey = None
            key_password = ""

            if self.session.auth_type == AuthType.KEY and self.session.key_path:
                pkey = self._load_key(self.session.key_path)
                if not pkey:
                    log.warning(f"Could not load key file: {self.session.key_path}")
            elif self.session.auth_type == AuthType.KEY_WITH_PASSWORD:
                if self.session.key_path:
                    pkey = self._load_key(self.session.key_path, password)
                    if not pkey:
                        log.warning(f"Could not load key file: {self.session.key_path}")
                if not pkey and password:
                    pass

            if pkey:
                self._transport.connect(
                    username=self.session.username,
                    pkey=pkey,
                )
            elif password:
                self._transport.connect(
                    username=self.session.username,
                    password=password,
                )
            else:
                agent = paramiko.Agent()
                agent_keys = agent.get_keys()
                if agent_keys:
                    self._transport.connect(
                        username=self.session.username,
                        pkey=agent_keys[0],
                    )
                else:
                    self._transport.connect(username=self.session.username)

            log.info(f"SFTP transport authenticated to {host}")
        except paramiko.AuthenticationException as e:
            self._transport = None
            raise ConnectionError(f"Authentication failed: {e}")
        except Exception as e:
            self._transport = None
            raise ConnectionError(f"SSH transport error: {e}")

        try:
            self._sftp = paramiko.SFTPClient.from_transport(self._transport)
            log.info(f"SFTP channel opened to {host}")
        except Exception as e:
            raise ConnectionError(f"SFTP channel failed: {e}")

    def _resolve_path(self, path: str) -> str:
        if path == "~" or path.startswith("~/"):
            home = self._get_home()
            if home:
                if path == "~":
                    return home
                rest = path[2:].lstrip("/")
                return home + "/" + rest
            return "."
        return path.replace("\\", "/")

    def _get_home(self) -> str:
        is_win = _is_windows_host(self.session.host)
        if is_win:
            cmds = [
                "echo %USERPROFILE%",
                "echo $env:USERPROFILE",
                "echo $HOME",
            ]
        else:
            cmds = ["echo $HOME"]
        for cmd in cmds:
            try:
                channel = self._transport.open_session()
                channel.exec_command(cmd)
                home = channel.recv(1024).decode().strip()
                channel.close()
                if home and not home.startswith("$") and not home.startswith("%"):
                    try:
                        self._sftp.stat(home)
                        return home
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            self._sftp.stat(".")
            return "."
        except Exception:
            return ""

    def list_dir(self, path: str = ".") -> list[dict]:
        if not self._sftp:
            raise ConnectionError("SFTP not connected")
        resolved = self._resolve_path(path)
        items = []
        try:
            for attr in self._sftp.listdir_attr(resolved):
                is_dir = attr.st_mode is not None and (attr.st_mode & 0o170000) == 0o040000
                items.append({
                    "name": attr.filename,
                    "is_dir": is_dir,
                    "size": attr.st_size or 0,
                    "mtime": attr.st_mtime or 0,
                    "permissions": attr.st_mode or 0,
                })
        except FileNotFoundError:
            raise FileNotFoundError(f"Directory not found: {resolved}")
        except Exception as e:
            log.error(f"SFTP list_dir error ({resolved}): {e}")
            raise
        items.sort(key=lambda x: (not x["is_dir"], x["name"]))
        return items

    def download(self, remote_path: str, local_path: str):
        if not self._sftp:
            raise ConnectionError("SFTP not connected")
        resolved = self._resolve_path(remote_path)
        self._sftp.get(resolved, local_path)
        log.info(f"SFTP download: {resolved} → {local_path}")

    def upload(self, local_path: str, remote_path: str):
        if not self._sftp:
            raise ConnectionError("SFTP not connected")
        resolved = self._resolve_path(remote_path)
        self._sftp.put(local_path, resolved)
        log.info(f"SFTP upload: {local_path} → {resolved}")

    def disconnect(self):
        try:
            if self._sftp:
                self._sftp.close()
        except Exception:
            pass
        self._sftp = None
        try:
            if self._transport:
                self._transport.close()
        except Exception:
            pass
        self._transport = None
        self._client = None
