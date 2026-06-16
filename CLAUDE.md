# JetdreamTerminal — MobaXterm Clone for Linux

## 🎯 Mission

สร้าง terminal client บน Linux ที่ทำหน้าที่เหมือน MobaXterm บน Windows
- **Shell** (local bash/zsh/fish — ปุ่ม Shell)
- **SSH** (standard + legacy mode สำหรับ Cisco/Aruba/older devices)
- **Telnet** (console server, legacy network devices)
- **RDP** (xfreerdp subprocess)
- **SFTP** (file browser panel + inline ใน SSH tab)
- **Serial** (console cable / USB-to-Serial adapter)

**Legacy device support สำคัญมาก:** Cisco 2960X, 3750, ASA 5500, Aruba switches

---

## 🔑 Tech Stack

| Layer | Library | Purpose |
|---|---|---|
| GUI | PyQt6 | Main window, tabs, dialogs |
| Terminal emulation | pyte | ANSI/VT100 → screen buffer (large buffer 5000+ rows) |
| PTY | python-pty (stdlib) | Fork shell/ssh/telnet ใน pseudoterminal |
| Async read | QSocketNotifier | non-blocking read master_fd → Qt signal |
| SSH/SFTP | paramiko | SSH command + SFTP via Transport |
| Serial | pyserial | USB-to-Serial adapter |
| Crypto | cryptography (Fernet) | Encrypt stored passwords |
| RDP | xfreerdp (system) | subprocess wrapper |
| Telnet | telnetlib / subprocess | Legacy device access |
| Storage | SQLite | Session persistence |
| Local shell | bash/zsh/fish | Shell mode |

---

## 📁 Project Structure

```
JetdreamTerminal/
├── CLAUDE.md                 ← ไฟล์นี้
├── requirements.txt
├── main.py                   ← Entry point
├── core/
│   ├── __init__.py
│   ├── pty_manager.py        ← PTY fork, QSocketNotifier, resize
│   ├── ssh_client.py         ← SSH command builder (standard + legacy)
│   ├── telnet_client.py      ← Telnet connection + PTY wrapper
│   ├── rdp_client.py         ← xfreerdp subprocess wrapper
│   ├── serial_client.py      ← pyserial + QTimer polling
│   ├── sftp_browser.py       ← paramiko Transport SFTP
│   ├── crypto.py             ← Fernet encrypt/decrypt
│   ├── session_manager.py    ← SQLite CRUD
│   └── host_key.py           ← ssh-keyscan + TOFU
├── ui/
│   ├── __init__.py
│   ├── main_window.py        ← MainWindow, sidebar, tabs, menus
│   ├── terminal_widget.py    ← pyte + QPainter + scroll + selection + bg image
│   ├── session_dialog.py     ← New/Edit session (with required field styling)
│   ├── ssh_tab.py            ← SSH tab with SFTP panel toggle
│   ├── telnet_tab.py         ← Telnet tab
│   ├── rdp_tab.py            ← RDP tab (xfreerdp embed)
│   ├── serial_tab.py         ← Serial tab with port/baud selector
│   ├── shell_tab.py          ← Local shell tab
│   ├── sftp_tab.py           ← SFTP standalone tab
│   ├── sftp_panel.py         ← SFTP file browser panel
│   ├── host_key_dialog.py    ← Host key TOFU dialog
│   ├── keygen_dialog.py      ← SSH Key Generator (with sshpass)
│   ├── settings_dialog.py    ← Settings: bg image, theme, opacity
│   └── theme.py              ← Nord dark theme + terminal themes + QSS
├── models/
│   ├── __init__.py
│   └── session.py            ← Session dataclass + enums
└── utils/
    ├── __init__.py
    ├── db.py                 ← SQLite connection + schema
    ├── config.py             ← paths + config load/save
    └── logger.py             ← file + console logging
```

---

## 🗃️ Session Model

```python
class SessionType(Enum):
    SSH = "ssh"
    TELNET = "telnet"
    RDP = "rdp"
    SFTP = "sftp"
    SERIAL = "serial"
    SHELL = "shell"

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
```

---

## 🔄 Connection Flows

### Shell (Local Terminal)
1. กดปุ่ม **⬛ Shell** → เปิด bash/zsh/fish ทันที
2. ไม่ต้องกรอก host/port/auth
3. ใช้ `$SHELL` environment variable

### SSH (Standard)
1. User double-click session → `MainWindow._open_session()`
2. Create `SSHTab(session)` → host key check (TOFU)
3. `PtyManager.launch(["ssh", user@host, ...], env)`
4. Password auto-login: `sshpass -e` + `SSHPASS` env var
5. SFTP panel: กดปุ่ม **📁 SFTP** ใน SSH tab เพื่อเปิด file browser

### SSH (Legacy — Cisco 2960X / Aruba)
1. Same flow but with extra `-o` flags:
   ```
   -o KexAlgorithms=+diffie-hellman-group1-sha1,diffie-hellman-group14-sha1
   -o HostKeyAlgorithms=+ssh-rsa,ssh-dss
   -o Ciphers=+aes128-cbc,3des-cbc
   -o MACs=+hmac-md5,hmac-sha1
   ```

### Telnet
1. `PtyManager.launch(["telnet", host, port])`

### Serial (Console Cable)
1. Auto-detect USB-to-Serial ports (`/dev/ttyUSB0`, `/dev/ttyACM0`)
2. `SerialManager.connect(port, baudrate)` ผ่าน pyserial
3. Toolbar เล็ก: Port combo + Baudrate + Connect/Disconnect
4. ใช้ `sshpass` สำหรับ auth

### RDP
1. `subprocess.Popen(["xfreerdp", f"/v:{host}", f"/u:{user}", ...])`

### SFTP (paramiko Transport)
1. ใช้ `paramiko.Transport` ตรง (ไม่ผ่าน SSHClient)
2. `socket.create_connection()` → `Transport.connect()` → `SFTPClient.from_transport()`
3. แก้ปัญหา "No existing session" ของ paramiko 5.0.0

---

## 🖥️ UI Layout

```
┌──────────────────────────────────────────────────────┐
│  Menu: File | Sessions | Tools(⚙Settings) | Help     │
├─────────────────┬────────────────────────────────────┤
│  🔍 Sessions    │  [SSH: srv1] [Serial: sw1] [+]     │
│                 ├────────────────────────────────────┤
│  Session        │  [📁 SFTP toggle]                   │
│  Sidebar        ├────────────────────────────────────┤
│                 │                                    │
│  ▼ Work         │   Terminal / SFTP / RDP            │
│    server1      │                                    │
│    cisco-sw1    │   Scrollback 5000+ lines           │
│  ▼ Network      │   Mouse selection + auto-copy      │
│    2960X-sw     │   Right-click: Copy/Paste/Theme    │
│                 ├────────────────────────────────────┤
│  [+ New Session]│  Status bar                        │
│  [⬛ Shell]     │                                    │
│  [🔑 Key Gen]   │                                    │
└─────────────────┴────────────────────────────────────┘
```

---

## 🎨 Terminal Features

### Scrollback
- ใช้ pyte Screen ขนาดใหญ่ (vis_rows + 5000)
- Mouse wheel: scroll 3 บรรทัด
- PageUp/PageDown: scroll ทีละหน้าจอ
- Scrollbar ด้านขวา + indicator "↑ X lines"
- Auto-scroll กลับเมื่อกด key หรือมีข้อมูลใหม่

### Unicode & Thai Text Support
- **ThaiScreen** (subclass `pyte.Screen`): override `draw()` เพื่อจัดการ combining characters
  - สระ/วรรณยุกต์ไทย (Unicode category "M") ถูก merge เข้า cell ก่อนหน้า ไม่ put ใน cell ใหม่
  - ใช้ `Char._replace(data=...)` ของ pyte namedtuple
- **Byte buffer**: `_byte_buffer` accumulates partial UTF-8 sequences ก่อน decode
- เปลี่ยนจาก `pyte.ByteStream` → `pyte.Stream` (text mode) + manual decode
- `unicodedata.category()` ใช้เช็ค combining marks (category "Mn", "Mc", "Me")

### Shift+Tab (Backtab)
- Qt6 แปลง Shift+Tab เป็น `Key_Backtab` อัตโนมัติ (ไม่ใช่ Key_Tab + ShiftModifier)
- ส่ง escape sequence `\x1b[Z` เข้า PTY ให้ app ใน terminal จัดการ
- ใช้สำหรับเปลี่ยน Mode ใน AI tools เช่น Claude Code / MiMoCode

### Copy/Paste
- **ลากเมาส์เลือก** → ปล่อย auto-copy → toast "Copied X line(s)"
- **Ctrl+Shift+C** = Copy (selection หรือทั้งหน้า)
- **Ctrl+Shift+V** = Paste
- **Ctrl+C** = SIGINT (ไม่ใช่ copy)
- **Ctrl+A/E/K/U/W/L/R** = readline shortcuts

### Background Image
- **Ctrl+,** หรือ Tools → Settings → Browse เลือกรูป
- แสดงตลอดแม้ยังไม่ connect
- Opacity slider 10%-100%
- 保存 ลง config.ini ถาวร

### Terminal Themes
- 11 themes: Nord, Dracula, Monokai, Solarized, Gruvbox, One Dark, Catppuccin, Tokyo Night, White, Black
- เปลี่ยนผ่าน Settings dialog

### Session Dialog
- **Required fields**: border สีแดง `#bf616a` + `*` label
- **Optional fields**: border สีเทา `#4c566a`
- Auto-detect serial ports พร้อม description
- SSH default auth = Key + Password

### SSH Key Generator
- ใช้ `sshpass` สำหรับ push key (ssh-copy-id)
- แสดง password field เมื่อ push key
- Key file = optional (SSH ใช้ default key อัตโนมัติ)

---

## 🔧 Serial Console

### Session Dialog
- Type: Serial
- Auto-detect USB-to-Serial ports (`/dev/ttyUSB0`, `/dev/ttyACM0`)
- Port combo + Refresh button + Baudrate selector
- แสดง port description เช่น "USB Serial", "FTDI"

### Serial Tab
- Toolbar เล็ก 32px: Port + Baud + Connect/Disconnect
- Auto-connect เมื่อเปิด tab
- Auto-focus terminal หลัง connect

---

## ⚙️ Config Paths

| File | Path |
|---|---|
| App config | `~/.config/jetdreamterminal/config.ini` |
| Encryption key | `~/.config/jetdreamterminal/key.bin` |
| Database | `~/.local/share/jetdreamterminal/sessions.db` |
| Logs | `~/.local/share/jetdreamterminal/app.log` |
| Known hosts | `~/.ssh/known_hosts` |

### Config Sections
```ini
[terminal]
theme = Nord
bg_image = /path/to/image.png
opacity = 0.85
```

---

## 🚀 Quick Start

```bash
cd /home/jetdream/HHD-Dream/JetdreamTerminal

python3 -m venv .venv
source .venv/bin/activate

pip install PyQt6 paramiko cryptography pyte pyserial

sudo apt install libxcb-cursor0 sshpass freerdp2-x11

python3 main.py
```

---

## 📋 Known Issues / Notes

- SFTP: ใช้ `paramiko.Transport` ตรง (ไม่ใช้ SSHClient) เพราะ paramiko 5.0.0 มีปัญหา "No existing session"
- DB migration: เพิ่ม `serial_port`, `baudrate` columns อัตโนมัติ
- Session type เดิม "console" → migrate เป็น "serial"
- Legacy SSH mode สำคัญมากสำหรับ work ที่ DataCom
- Key file = optional เพราะ SSH ใช้ default key หลัง ssh-copy-id แล้ว
