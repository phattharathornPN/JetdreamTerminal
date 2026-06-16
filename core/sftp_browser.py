import paramiko
import os
import socket
from models.session import Session
from core.crypto import decrypt
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

            if password:
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
            try:
                channel = self._transport.open_session()
                channel.exec_command("echo $HOME")
                home = channel.recv(1024).decode().strip()
                channel.close()
                if path == "~":
                    return home
                return home + path[1:]
            except Exception:
                return path
        return path

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
