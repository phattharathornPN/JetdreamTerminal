import sqlite3
from utils.config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            session_type TEXT NOT NULL DEFAULT 'ssh',
            host TEXT DEFAULT '',
            port INTEGER DEFAULT 22,
            username TEXT DEFAULT '',
            auth_type TEXT DEFAULT 'password',
            password_encrypted BLOB DEFAULT X'',
            key_path TEXT DEFAULT '',
            grp TEXT DEFAULT 'Default',
            created_at TEXT DEFAULT (datetime('now')),
            last_used TEXT DEFAULT '',
            legacy_mode INTEGER DEFAULT 0,
            rdp_width INTEGER DEFAULT 1920,
            rdp_height INTEGER DEFAULT 1080,
            serial_port TEXT DEFAULT '/dev/ttyUSB0',
            baudrate INTEGER DEFAULT 9600
        );
    """)
    cursor = conn.execute("PRAGMA table_info(sessions)")
    columns = {row["name"] for row in cursor.fetchall()}
    if "serial_port" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN serial_port TEXT DEFAULT '/dev/ttyUSB0'")
    if "baudrate" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN baudrate INTEGER DEFAULT 9600")
    if "favorite" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN favorite INTEGER DEFAULT 0")
    if "auto_save" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN auto_save INTEGER DEFAULT 0")
    if "vpn_realm" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN vpn_realm TEXT DEFAULT ''")
    if "vpn_trusted_cert" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN vpn_trusted_cert TEXT DEFAULT ''")
    if "vpn_ignore_cert" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN vpn_ignore_cert INTEGER DEFAULT 0")
    conn.execute("UPDATE sessions SET session_type='serial' WHERE session_type='console'")
    conn.commit()
    conn.close()
