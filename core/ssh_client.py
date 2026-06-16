from models.session import Session, SessionType, AuthType


def build_ssh_command(session: Session, password: str = "") -> tuple[list[str], dict]:
    cmd = ["ssh"]
    env = {}

    if session.legacy_mode:
        cmd += [
            "-o", "KexAlgorithms=+diffie-hellman-group1-sha1,diffie-hellman-group14-sha1",
            "-o", "HostKeyAlgorithms=+ssh-rsa,ssh-dss",
            "-o", "Ciphers=+aes128-cbc,3des-cbc",
            "-o", "MACs=+hmac-md5,hmac-sha1",
            "-o", "PubkeyAcceptedAlgorithms=+ssh-rsa",
        ]

    cmd += ["-o", "StrictHostKeyChecking=accept-new"]
    cmd += ["-p", str(session.port)]

    if session.auth_type == AuthType.KEY and session.key_path:
        cmd += ["-i", session.key_path]

    if session.auth_type in (AuthType.PASSWORD, AuthType.KEY_WITH_PASSWORD) and password:
        env["SSHPASS"] = password
        cmd += ["-o", "PreferredAuthentications=password,keyboard-interactive"]
        cmd = ["sshpass", "-e"] + cmd

    user_host = f"{session.username}@{session.host}" if session.username else session.host
    cmd.append(user_host)

    return cmd, env


def build_telnet_command(session: Session) -> list[str]:
    return ["telnet", session.host, str(session.port)]
