# AGENTS.md — JetdreamTerminal

## What this is

PyQt6 terminal client for Linux (MobaXterm clone). Supports SSH, Telnet, RDP, Serial, SFTP, VPN, VNC, and local shell. Python 3.12, single-user desktop app. Not a library — no tests, no CI.

## Run

```bash
# From project root
source .venv/bin/activate
python3 main.py
```

Or use `./launch.sh` (activates venv automatically).

## Dependencies

- **Python packages** (in `.venv`): `PyQt6`, `paramiko`, `cryptography`, `pyte`, `pyserial`
- **System packages** (must be installed separately): `libxcb-cursor0`, `sshpass`, `freerdp2-x11`, `tigervnc-viewer`
- `install.sh` auto-creates `.venv` + installs packages + sets up desktop entry. No hardcoded paths — safe to clone anywhere.

## Architecture

- **Entry point**: `main.py` → `MainWindow`
- **Connection types**: Each has a `*_tab.py` in `ui/` — some have companion modules in `core/`
  - `ssh_tab.py` ↔ `core/ssh_client.py` (SSH command builder, legacy mode flags)
  - `telnet_tab.py` — no separate client; uses `build_telnet_command()` from `ssh_client.py`, launches via `PtyManager`
  - `serial_tab.py` ↔ `core/serial_client.py` (pyserial + QTimer polling)
  - `rdp_tab.py` ↔ `core/rdp_client.py` (xfreerdp subprocess)
  - `sftp_tab.py` ↔ `core/sftp_browser.py` (paramiko Transport — **not** SSHClient)
  - `vpn_tab.py` — no separate client; runs `sudo openfortivpn` via `PtyManager`
  - `vnc_tab.py` ↔ `core/vnc_client.py` (vncviewer/remmina subprocess)
  - `shell_tab.py` — no client; launches `$SHELL` via `PtyManager`
- **Terminal rendering**: `terminal_widget.py` uses `pyte` screen buffer with custom `ThaiScreen` subclass for Thai/combining character support. Screen size = visible rows + 5000 scrollback. `ui/highlight.py` provides regex-based syntax highlighting (IPs, paths, errors, keywords).
- **PTY management**: `core/pty_manager.py` forks child process, uses `QSocketNotifier` for async reads.
- **Data persistence**: SQLite via `utils/db.py`. Schema auto-migrates (adds columns if missing). DB lives at `~/.local/share/jetdreamterminal/sessions.db`.
- **Credentials**: Fernet encryption via `core/crypto.py`. Key at `~/.config/jetdreamterminal/key.bin`.

## Gotchas

- **paramiko SFTP**: Uses `paramiko.Transport` directly, not `SSHClient`. paramiko 5.0.0 has a "No existing session" bug with SSHClient. Don't refactor to SSHClient without testing.
- **Legacy SSH mode**: Extra `-o` flags for Cisco/Aruba older devices (including `PubkeyAcceptedAlgorithms=+ssh-rsa`). This is critical for the user's network work — don't simplify these flags.
- **DB migration**: `init_db()` runs ALTER TABLE for new columns (currently: `serial_port`, `baudrate`, `favorite`, `auto_save`, `vpn_realm`, `vpn_trusted_cert`, `vpn_ignore_cert`, `vnc_port`). Don't add columns without adding migration logic in `utils/db.py:init_db()`.
- **Session type rename**: Old type "console" is migrated to "serial" on startup. Don't reintroduce "console" as a session type.
- **Thai text**: `ThaiScreen.draw()` merges combining marks (Unicode category "M") into the previous cell. If you touch terminal rendering, preserve this logic.
- **Cursor rendering**: Cursor position must use screen-relative coordinates (`cursor.y - top`), not raw `cursor.y` (buffer row). Buffer row grows with output → cursor drawn off-screen. See `terminal_widget.py` paintEvent cursor block.
- **Key file optional**: SSH sessions can omit key_path — SSH uses default key after `ssh-copy-id`. Don't make key_path required.
- **Host key verification**: `ssh-keyscan` must receive legacy flags (`KexAlgorithms`, `HostKeyAlgorithms`) for Cisco/Aruba devices. Dialog shows SHA256 fingerprints. Legacy devices that fail keyscan skip the dialog and connect directly.
- **Key filename**: Colons (`:`) in key filenames break `ssh-copy-id`. `keygen_dialog.py` rejects `:*?` in filenames.
- **ssh-copy-id flags**: Must pass `-o PreferredAuthentications=password,keyboard-interactive -o PubkeyAuthentication=no` for legacy devices that reject pubkey auth on first connect.
- **Desktop shortcut**: Ubuntu/GNOME requires `gio set metadata::trusted true` on `.desktop` files — `install.sh` handles this.
- **Symlink resolution**: `launch.sh` uses `readlink -f` to resolve symlinks. Without it, `cd $(dirname "$0")` lands in `/usr/local/bin/` instead of the app dir.
- **VPN uses openfortivpn**, not OpenConnect. Requires `sudo` — the app runs `sudo -S openfortivpn` via the PTY.
- **Auto-reconnect**: SSH and Telnet tabs auto-reconnect up to 3 times on non-zero exit with increasing delay (1s, 2s, 3s). Don't change this without testing.
- **Auto-save**: Sessions with `auto_save=True` save terminal output to `~/JetdreamTerminal-logs/` on close.
- **Windows SSH support**: SSH to Windows hosts (OpenSSH on Windows Server / Windows 10+). `_is_windows_host()` heuristic detects non-IP hostnames (WIN-*, DESKTOP-*, DC-*, etc.). Adds `RequestTTY=yes` and `TERM=xterm-256color`.
- **Windows SFTP**: `_resolve_path()` tries `%USERPROFILE%` → `$env:USERPROFILE` → `$HOME` with `sftp.stat()` validation. Falls back to `.` if all fail. Path separators normalized to `/`.
- **VNC**: Uses `vncviewer` (tigervnc) as primary viewer, falls back to remmina/xtightvncviewer. TigerVNC requires `host::port` (double colon) for explicit port. Password file uses binary XOR encoding, not plain text.
- **VNC password file**: TigerVNC `PasswordFile` format is 8 bytes XOR-encrypted with fixed key — not plain text. See `core/vnc_client.py:_make_vnc_password()`.

## No lint/test/format

This repo has no linter, test suite, or formatter configured. If you add code, match the existing style: no type hints in most files, `snake_case`, minimal comments.
