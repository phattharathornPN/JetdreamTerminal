from enum import Enum
from dataclasses import dataclass, field


class SessionType(Enum):
    SSH = "ssh"
    TELNET = "telnet"
    RDP = "rdp"
    SFTP = "sftp"
    SERIAL = "serial"
    SHELL = "shell"
    VPN = "vpn"
    VNC = "vnc"


class AuthType(Enum):
    PASSWORD = "password"
    KEY = "key"
    KEY_WITH_PASSWORD = "key_with_password"
    NONE = "none"


@dataclass
class Session:
    name: str = ""
    session_type: SessionType = SessionType.SSH
    host: str = ""
    port: int = 22
    username: str = ""
    auth_type: AuthType = AuthType.KEY_WITH_PASSWORD
    password_encrypted: bytes = b""
    key_path: str = ""
    group: str = "Default"
    id: int = 0
    created_at: str = ""
    last_used: str = ""
    legacy_mode: bool = False
    rdp_width: int = 1920
    rdp_height: int = 1080
    serial_port: str = "/dev/ttyUSB0"
    baudrate: int = 9600
    favorite: bool = False
    auto_save: bool = False
    vpn_realm: str = ""
    vpn_trusted_cert: str = ""
    vpn_ignore_cert: bool = False
    vnc_port: int = 5901

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "session_type": self.session_type.value,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "auth_type": self.auth_type.value,
            "password_encrypted": self.password_encrypted.hex() if self.password_encrypted else "",
            "key_path": self.key_path,
            "group": self.group,
            "id": self.id,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "legacy_mode": self.legacy_mode,
            "rdp_width": self.rdp_width,
            "rdp_height": self.rdp_height,
            "serial_port": self.serial_port,
            "baudrate": self.baudrate,
            "favorite": self.favorite,
            "auto_save": self.auto_save,
            "vpn_realm": self.vpn_realm,
            "vpn_trusted_cert": self.vpn_trusted_cert,
            "vpn_ignore_cert": self.vpn_ignore_cert,
            "vnc_port": self.vnc_port,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Session":
        pw_hex = d.get("password_encrypted", "")
        return cls(
            name=d.get("name", ""),
            session_type=SessionType(d.get("session_type", "ssh")),
            host=d.get("host", ""),
            port=d.get("port", 22),
            username=d.get("username", ""),
            auth_type=AuthType(d.get("auth_type", "password")),
            password_encrypted=bytes.fromhex(pw_hex) if pw_hex else b"",
            key_path=d.get("key_path", ""),
            group=d.get("group", "Default"),
            id=d.get("id", 0),
            created_at=d.get("created_at", ""),
            last_used=d.get("last_used", ""),
            legacy_mode=d.get("legacy_mode", False),
            rdp_width=d.get("rdp_width", 1920),
            rdp_height=d.get("rdp_height", 1080),
            serial_port=d.get("serial_port", "/dev/ttyUSB0"),
            baudrate=d.get("baudrate", 9600),
            favorite=d.get("favorite", False),
            auto_save=d.get("auto_save", False),
            vpn_realm=d.get("vpn_realm", ""),
            vpn_trusted_cert=d.get("vpn_trusted_cert", ""),
            vpn_ignore_cert=d.get("vpn_ignore_cert", False),
            vnc_port=d.get("vnc_port", 5900),
        )
