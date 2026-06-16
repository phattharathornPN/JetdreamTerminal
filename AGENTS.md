# AGENTS.md — JetdreamTerminal

## What this is

PyQt6 terminal client for Linux (MobaXterm clone). Supports SSH, Telnet, RDP, Serial, SFTP, VPN, and local shell. Python 3.12, single-user desktop app. Not a library — no tests, no CI.

## Run

```bash
# From project root
source .venv/bin/activate
python3 main.py
```

Or use `./launch.sh` (activates venv automatically).

## Dependencies

- **Python packages** (in `.venv`): `PyQt6`, `paramiko`, `cryptography`, `pyte`, `pyserial`
- **System packages** (must be installed separately): `libxcb-cursor0`, `sshpass`, `freerdp2-x11`
- `install.sh` does `sudo ln -sf` for the launch script — don't run without understanding it creates symlinks.

## Architecture

- **Entry point**: `main.py` → `MainWindow`
- **Connection types**: Each has a `*_tab.py` in `ui/` and a `*_client.py` in `core/`
  - `ssh_tab.py` ↔ `ssh_client.py` (SSH command builder, legacy mode flags)
  - `telnet_tab.py` ↔ `telnet_client.py` (subprocess telnet)
  - `serial_tab.py` ↔ `serial_client.py` (pyserial + QTimer polling)
  - `rdp_tab.py` ↔ `rdp_client.py` (xfreerdp subprocess)
  - `sftp_tab.py` ↔ `sftp_browser.py` (paramiko Transport — **not** SSHClient)
  - `vpn_tab.py` ↔ subprocess (OpenConnect/CLI VPN wrapper)
- **Terminal rendering**: `terminal_widget.py` uses `pyte` screen buffer with custom `ThaiScreen` subclass for Thai/combining character support. Screen size = visible rows + 5000 scrollback.
- **PTY management**: `pty_manager.py` forks child process, uses `QSocketNotifier` for async reads.
- **Data persistence**: SQLite via `utils/db.py`. Schema auto-migrates (adds columns if missing). DB lives at `~/.local/share/jetdreamterminal/sessions.db`.
- **Credentials**: Fernet encryption via `core/crypto.py`. Key at `~/.config/jetdreamterminal/key.bin`.

## Gotchas

- **paramiko SFTP**: Uses `paramiko.Transport` directly, not `SSHClient`. paramiko 5.0.0 has a "No existing session" bug with SSHClient. Don't refactor to SSHClient without testing.
- **Legacy SSH mode**: Extra `-o` flags for Cisco/Aruba older devices. This is critical for the user's network work — don't simplify these flags.
- **DB migration**: `init_db()` runs ALTER TABLE for new columns. Don't add columns without adding migration logic in `utils/db.py:init_db()`.
- **Session type rename**: Old type "console" is migrated to "serial" on startup. Don't reintroduce "console" as a session type.
- **Thai text**: `ThaiScreen.draw()` merges combining marks (Unicode category "M") into the previous cell. If you touch terminal rendering, preserve this logic.
- **Cursor rendering**: Cursor position must use screen-relative coordinates (`cursor.y - top`), not raw `cursor.y` (buffer row). Buffer row grows with output → cursor drawn off-screen. See `terminal_widget.py` paintEvent cursor block.
- **Key file optional**: SSH sessions can omit key_path — SSH uses default key after `ssh-copy-id`. Don't make key_path required.

## No lint/test/format

This repo has no linter, test suite, or formatter configured. If you add code, match the existing style: no type hints in most files, `snake_case`, minimal comments.
