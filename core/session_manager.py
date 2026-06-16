from datetime import datetime
from models.session import Session
from utils.db import get_conn


def save(session: Session) -> int:
    conn = get_conn()
    now = datetime.now().isoformat()
    if session.id:
        conn.execute("""
            UPDATE sessions SET
                name=?, session_type=?, host=?, port=?, username=?,
                auth_type=?, password_encrypted=?, key_path=?, grp=?,
                last_used=?, legacy_mode=?,
                rdp_width=?, rdp_height=?, serial_port=?, baudrate=?,
                favorite=?, auto_save=?, vpn_realm=?, vpn_trusted_cert=?, vpn_ignore_cert=?
            WHERE id=?
        """, (
            session.name, session.session_type.value, session.host,
            session.port, session.username, session.auth_type.value,
            session.password_encrypted, session.key_path, session.group,
            session.last_used, session.legacy_mode,
            session.rdp_width, session.rdp_height,
            session.serial_port, session.baudrate,
            session.favorite, session.auto_save,
            session.vpn_realm, session.vpn_trusted_cert, session.vpn_ignore_cert, session.id,
        ))
        conn.commit()
        conn.close()
        return session.id
    else:
        cur = conn.execute("""
            INSERT INTO sessions
                (name, session_type, host, port, username, auth_type,
                 password_encrypted, key_path, grp, created_at,
                 legacy_mode, rdp_width, rdp_height,
                 serial_port, baudrate, favorite, auto_save,
                 vpn_realm, vpn_trusted_cert, vpn_ignore_cert)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.name, session.session_type.value, session.host,
            session.port, session.username, session.auth_type.value,
            session.password_encrypted, session.key_path, session.group,
            now, session.legacy_mode,
            session.rdp_width, session.rdp_height,
            session.serial_port, session.baudrate,
            session.favorite, session.auto_save,
            session.vpn_realm, session.vpn_trusted_cert, session.vpn_ignore_cert,
        ))
        conn.commit()
        row_id = cur.lastrowid
        conn.close()
        return row_id


def load_all() -> list[Session]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM sessions ORDER BY favorite DESC, grp, name").fetchall()
    conn.close()
    sessions = []
    for r in rows:
        s = Session(
            id=r["id"],
            name=r["name"],
            session_type=__import__("models.session", fromlist=["SessionType"]).SessionType(r["session_type"]),
            host=r["host"],
            port=r["port"],
            username=r["username"],
            auth_type=__import__("models.session", fromlist=["AuthType"]).AuthType(r["auth_type"]),
            password_encrypted=r["password_encrypted"] or b"",
            key_path=r["key_path"],
            group=r["grp"],
            created_at=r["created_at"],
            last_used=r["last_used"],
            legacy_mode=bool(r["legacy_mode"]),
            rdp_width=r["rdp_width"],
            rdp_height=r["rdp_height"],
            serial_port=r["serial_port"] if "serial_port" in r.keys() else "/dev/ttyUSB0",
            baudrate=r["baudrate"] if "baudrate" in r.keys() else 9600,
            favorite=bool(r["favorite"]) if "favorite" in r.keys() else False,
            auto_save=bool(r["auto_save"]) if "auto_save" in r.keys() else False,
            vpn_realm=r["vpn_realm"] if "vpn_realm" in r.keys() else "",
            vpn_trusted_cert=r["vpn_trusted_cert"] if "vpn_trusted_cert" in r.keys() else "",
            vpn_ignore_cert=bool(r["vpn_ignore_cert"]) if "vpn_ignore_cert" in r.keys() else False,
        )
        sessions.append(s)
    return sessions


def delete(session_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
    conn.commit()
    conn.close()


def get_by_id(session_id: int) -> Session | None:
    conn = get_conn()
    r = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    conn.close()
    if not r:
        return None
    from models.session import SessionType, AuthType
    return Session(
        id=r["id"],
        name=r["name"],
        session_type=SessionType(r["session_type"]),
        host=r["host"],
        port=r["port"],
        username=r["username"],
        auth_type=AuthType(r["auth_type"]),
        password_encrypted=r["password_encrypted"] or b"",
        key_path=r["key_path"],
        group=r["grp"],
        created_at=r["created_at"],
        last_used=r["last_used"],
        legacy_mode=bool(r["legacy_mode"]),
        rdp_width=r["rdp_width"],
        rdp_height=r["rdp_height"],
        favorite=bool(r["favorite"]) if "favorite" in r.keys() else False,
        auto_save=bool(r["auto_save"]) if "auto_save" in r.keys() else False,
        vpn_realm=r["vpn_realm"] if "vpn_realm" in r.keys() else "",
        vpn_trusted_cert=r["vpn_trusted_cert"] if "vpn_trusted_cert" in r.keys() else "",
        vpn_ignore_cert=bool(r["vpn_ignore_cert"]) if "vpn_ignore_cert" in r.keys() else False,
    )


def update_last_used(session_id: int):
    conn = get_conn()
    conn.execute(
        "UPDATE sessions SET last_used=? WHERE id=?",
        (datetime.now().isoformat(), session_id),
    )
    conn.commit()
    conn.close()
