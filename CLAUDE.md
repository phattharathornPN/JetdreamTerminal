# JetdreamTerminal — MobaXterm Clone for Linux

## Mission

สร้าง terminal client บน Linux ที่ทำหน้าที่เหมือน MobaXterm บน Windows
- **Shell** (local bash/zsh/fish)
- **SSH** (standard + legacy mode สำหรับ Cisco/Aruba/older devices)
- **Telnet** (console server, legacy network devices)
- **RDP** (xfreerdp subprocess)
- **SFTP** (file browser panel + inline ใน SSH tab)
- **Serial** (console cable / USB-to-Serial adapter)
- **VPN** (openfortivpn)
- **VNC** (vncviewer/remmina)

**Legacy device support สำคัญมาก:** Cisco 2960X, 3750, ASA 5500, Aruba switches

---

## Tech Stack

| Layer | Library | Purpose |
|---|---|---|
| GUI | PyQt6 | Main window, tabs, dialogs |
| Terminal emulation | pyte | ANSI/VT100 → screen buffer (large buffer 5000+ rows). ThaiScreen overrides set_mode/reset_mode for alternate screen (DECSET 1049) — pyte 0.8.2 doesn't handle this. |
| PTY | python-pty (stdlib) | Fork shell/ssh/telnet ใน pseudoterminal |
| Async read | QSocketNotifier | non-blocking read master_fd → Qt signal |
| SSH/SFTP | paramiko | SSH command + SFTP via Transport |
| Serial | pyserial | USB-to-Serial adapter |
| Crypto | cryptography (Fernet) | Encrypt stored passwords |
| RDP | xfreerdp (system) | subprocess wrapper |
| VNC | vncviewer/remmina (system) | subprocess wrapper |
| VPN | openfortivpn (system) | subprocess wrapper |
| Storage | SQLite | Session persistence |
| Local shell | bash/zsh/fish | Shell mode |

---

## Project Structure

```
JetdreamTerminal/
├── CLAUDE.md
├── AGENTS.md
├── requirements.txt
├── main.py                   ← Entry point
├── core/
│   ├── pty_manager.py        ← PTY fork, QSocketNotifier, resize
│   ├── ssh_client.py         ← SSH command builder (standard + legacy + Windows detect)
│   ├── rdp_client.py         ← xfreerdp subprocess wrapper
│   ├── vnc_client.py         ← vncviewer/remmina subprocess wrapper
│   ├── serial_client.py      ← pyserial + QTimer polling
│   ├── sftp_browser.py       ← paramiko Transport SFTP (Windows path support)
│   ├── crypto.py             ← Fernet encrypt/decrypt
│   ├── session_manager.py    ← SQLite CRUD
│   └── host_key.py           ← ssh-keyscan + TOFU
├── ui/
│   ├── main_window.py        ← MainWindow, sidebar, tabs, menus
│   ├── terminal_widget.py    ← pyte + QPainter + scroll + selection + bg image
│   ├── session_dialog.py     ← New/Edit session (SSH/Telnet/RDP/SFTP/Serial/VPN/VNC)
│   ├── ssh_tab.py            ← SSH tab with SFTP panel toggle
│   ├── telnet_tab.py         ← Telnet tab
│   ├── rdp_tab.py            ← RDP tab (xfreerdp)
│   ├── vnc_tab.py            ← VNC tab (host + port only)
│   ├── serial_tab.py         ← Serial tab with port/baud selector
│   ├── shell_tab.py          ← Local shell tab
│   ├── sftp_tab.py           ← SFTP standalone tab
│   ├── sftp_panel.py         ← SFTP file browser panel (Windows path support)
│   ├── vpn_tab.py            ← VPN tab (openfortivpn)
│   ├── host_key_dialog.py    ← Host key TOFU dialog
│   ├── keygen_dialog.py      ← SSH Key Generator (with sshpass)
│   ├── settings_dialog.py    ← Settings: bg image, theme, opacity
│   ├── highlight.py          ← Regex syntax highlighting
│   └── theme.py              ← Nord dark theme + terminal themes + QSS
├── models/
│   └── session.py            ← Session dataclass + enums (SSH/Telnet/RDP/SFTP/Serial/Shell/VPN/VNC)
└── utils/
    ├── db.py                 ← SQLite connection + schema
    ├── config.py             ← paths + config load/save
    └── logger.py             ← file + console logging
```

---

## Session Model

```python
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
    name:               str
    session_type:       SessionType
    host:               str = ""
    port:               int = 22
    username:           str = ""
    auth_type:          AuthType = AuthType.KEY_WITH_PASSWORD
    password_encrypted: bytes = b""
    key_path:           str = ""
    group:              str = "Default"
    id:                 int = 0
    created_at:         str = ""
    last_used:          str = ""
    legacy_mode:        bool = False
    rdp_width:          int = 1920
    rdp_height:         int = 1080
    serial_port:        str = "/dev/ttyUSB0"
    baudrate:           int = 9600
    favorite:           bool = False
    auto_save:          bool = False
    vpn_realm:          str = ""
    vpn_trusted_cert:   str = ""
    vpn_ignore_cert:    bool = False
    vnc_port:           int = 5901
```

---

## Connection Flows

### Shell (Local Terminal)
1. กดปุ่ม **Shell** → เปิด bash/zsh/fish ทันที
2. ไม่ต้องกรอก host/port/auth
3. ใช้ `$SHELL` environment variable

### SSH (Standard)
1. User double-click session → `MainWindow._open_session()`
2. Create `SSHTab(session)` → host key check (TOFU)
3. `PtyManager.launch(["ssh", user@host, ...], env)`
4. Password auto-login: `sshpass -e` + `SSHPASS` env var
5. SFTP panel: กดปุ่ม **SFTP** ใน SSH tab เพื่อเปิด file browser

### SSH (Legacy — Cisco 2960X / Aruba)
Same flow but with extra `-o` flags:
```
-o KexAlgorithms=+diffie-hellman-group1-sha1,diffie-hellman-group14-sha1
-o HostKeyAlgorithms=+ssh-rsa,ssh-dss
-o Ciphers=+aes128-cbc,3des-cbc
-o MACs=+hmac-md5,hmac-sha1
```

### SSH (Windows)
Same flow but with extra options:
```
-o RequestTTY=yes
-o SendEnv=TERM LANG
```
Terminal sets `TERM=xterm-256color`.

### Telnet
`PtyManager.launch(["telnet", host, port])`

### Serial (Console Cable)
1. Auto-detect USB-to-Serial ports (`/dev/ttyUSB0`, `/dev/ttyACM0`)
2. `SerialManager.connect(port, baudrate)` ผ่าน pyserial
3. Toolbar: Port combo + Baudrate + Connect/Disconnect

### RDP
`subprocess.Popen(["xfreerdp", f"/v:{host}", f"/u:{user}", ...])`

### VNC
1. User enters host + port in VNC tab
2. `VncClient.launch()` finds vncviewer/remmina
3. TigerVNC uses `host::port` (double colon) for explicit port
4. Password file uses binary XOR encoding (8 bytes)

### SFTP (paramiko Transport)
1. ใช้ `paramiko.Transport` ตรง (ไม่ผ่าน SSHClient)
2. `socket.create_connection()` → `Transport.connect()` → `SFTPClient.from_transport()`
3. แก้ปัญหา "No existing session" ของ paramiko 5.0.0
4. Windows: `_resolve_path()` ใช้ `%USERPROFILE%` แทน `$HOME`

### VPN
`sudo -S openfortivpn host:port -u user -r realm --trusted-cert hash`

---

## Config Paths

| File | Path |
|---|---|
| App config | `~/.config/jetdreamterminal/config.ini` |
| Encryption key | `~/.config/jetdreamterminal/key.bin` |
| Database | `~/.local/share/jetdreamterminal/sessions.db` |
| Logs | `~/.local/share/jetdreamterminal/app.log` |
| Known hosts | `~/.ssh/known_hosts` |

---

## Known Issues

- SFTP ใช้ `paramiko.Transport` ตรง (ไม่ใช้ SSHClient) เพราะ paramiko 5.0.0 มีปัญหา "No existing session"
- DB migration: เพิ่ม columns อัตโนมัติ — ดู `utils/db.py:init_db()`
- Session type เดิม "console" → migrate เป็น "serial"
- Legacy SSH mode สำคัญมากสำหรับ work ที่ DataCom
- Key file = optional เพราะ SSH ใช้ default key หลัง ssh-copy-id แล้ว
- VNC password file ต้องเป็น binary format (XOR) ไม่ใช่ plain text
- **Alternate screen buffer**: pyte 0.8.2 ไม่รองรับ DECSET/DECRST 1049 — `ThaiScreen` override `set_mode`/`reset_mode` เพื่อ save/restore buffer + cursor ตอนเข้า/ออกจาก alternate screen. ถ้าไม่มี override นี้ `htop` และ `systemctl status` จะทำลาย scrollback buffer ตอนออกจาก program. ห้ามลบ `_saved_alt_buffer`/`_saved_alt_cursor`
