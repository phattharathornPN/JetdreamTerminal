import os
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QLabel, QTextEdit, QFileDialog,
    QMessageBox, QGroupBox,
)
from PyQt6.QtCore import Qt
from utils.logger import log


class KeygenDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SSH Key Generator")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self._setup_ui()
        self._center_on_parent()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        gen_group = QGroupBox("Generate New Key Pair")
        gen_layout = QFormLayout()

        self._key_type = QComboBox()
        self._key_type.addItems(["ed25519", "rsa-4096", "ecdsa"])
        self._key_type.currentIndexChanged.connect(self._on_key_type_changed)
        gen_layout.addRow("Key type:", self._key_type)

        self._key_comment = QLineEdit()
        self._key_comment.setPlaceholderText("user@hostname")
        gen_layout.addRow("Comment:", self._key_comment)

        self._key_file = QLineEdit()
        self._key_file.setPlaceholderText("~/.ssh/id_ed25519")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_key)
        file_layout = QHBoxLayout()
        file_layout.addWidget(self._key_file)
        file_layout.addWidget(browse_btn)
        gen_layout.addRow("Output file:", file_layout)

        self._gen_btn = QPushButton("Generate Key")
        self._gen_btn.clicked.connect(self._generate_key)
        gen_layout.addRow("", self._gen_btn)

        gen_group.setLayout(gen_layout)
        layout.addWidget(gen_group)

        push_group = QGroupBox("Push Public Key to Server (ssh-copy-id)")
        push_layout = QFormLayout()

        self._push_user = QLineEdit()
        self._push_user.setPlaceholderText("username")
        push_layout.addRow("Username:", self._push_user)

        self._push_host = QLineEdit()
        self._push_host.setPlaceholderText("hostname or IP")
        push_layout.addRow("Host:", self._push_host)

        self._push_key = QLineEdit()
        self._push_key.setPlaceholderText("~/.ssh/id_ed25519.pub")
        push_browse = QPushButton("Browse")
        push_browse.clicked.connect(self._browse_pub)
        push_file = QHBoxLayout()
        push_file.addWidget(self._push_key)
        push_file.addWidget(push_browse)
        push_layout.addRow("Public key:", push_file)

        self._push_password = QLineEdit()
        self._push_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._push_password.setPlaceholderText("password for ssh-copy-id")
        push_layout.addRow("Password:", self._push_password)

        self._push_btn = QPushButton("Push Key")
        self._push_btn.clicked.connect(self._push_key_to_server)
        push_layout.addRow("", self._push_btn)

        push_group.setLayout(push_layout)
        layout.addWidget(push_group)

        REQUIRED = "border: 2px solid #bf616a; border-radius: 3px; background: #3b2025;"
        OPTIONAL = "border: 1px solid #4c566a; border-radius: 3px;"
        self._push_user.setStyleSheet(REQUIRED)
        self._push_host.setStyleSheet(REQUIRED)
        self._push_password.setStyleSheet(REQUIRED)
        self._push_key.setStyleSheet(OPTIONAL)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setMaximumHeight(120)
        layout.addWidget(self._output)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _browse_key(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Private Key", os.path.expanduser("~/.ssh/id_ed25519")
        )
        if path:
            self._key_file.setText(path)

    def _browse_pub(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Public Key", os.path.expanduser("~/.ssh"),
            "Public Keys (*.pub);;All Files (*)"
        )
        if path:
            self._push_key.setText(path)

    def _on_key_type_changed(self):
        type_map = {0: "ed25519", 1: "rsa", 2: "ecdsa"}
        key_type = type_map.get(self._key_type.currentIndex(), "ed25519")
        default_path = os.path.expanduser(f"~/.ssh/id_{key_type}")
        self._key_file.setPlaceholderText(default_path)

    def _generate_key(self):
        type_map = {0: ("ed25519", ["-t", "ed25519"]), 1: ("rsa", ["-t", "rsa", "-b", "4096"]), 2: ("ecdsa", ["-t", "ecdsa"])}
        idx = self._key_type.currentIndex()
        key_type, key_args = type_map.get(idx, ("ed25519", ["-t", "ed25519"]))
        comment = self._key_comment.text().strip()
        key_file = self._key_file.text().strip() or os.path.expanduser(f"~/.ssh/id_{key_type}")

        if ":" in key_file or "*" in key_file or "?" in key_file:
            QMessageBox.warning(
                self, "Invalid filename",
                "Key filename cannot contain : * ?\n\n"
                "These characters break ssh-copy-id and SSH."
            )
            return

        if os.path.exists(key_file):
            reply = QMessageBox.question(
                self, "Overwrite?",
                f"Key file already exists:\n{key_file}\n\nOverwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        cmd = ["ssh-keygen"] + key_args + ["-f", key_file, "-N", ""]
        if comment:
            cmd += ["-C", comment]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30,
                input="y\n",
            )
            self._output.append(result.stdout)
            if result.stderr:
                self._output.append(result.stderr)
            if result.returncode == 0:
                self._output.append(f"\n✅ Key generated: {key_file}")
                pub_file = key_file + ".pub"
                if os.path.exists(pub_file):
                    with open(pub_file) as f:
                        self._output.append(f"\nPublic key:\n{f.read()}")
                    self._push_key.setText(pub_file)
        except Exception as e:
            self._output.append(f"Error: {e}")

    def _detect_authorized_keys_path(self, user, host, password):
        cmd = ["ssh", "-o", "StrictHostKeyChecking=accept-new"]
        cmd += [f"{user}@{host}", "sshd -T 2>/dev/null | grep authorizedkeysfile"]
        env = os.environ.copy()
        if password:
            cmd = ["sshpass", "-e"] + ["ssh", "-o", "StrictHostKeyChecking=accept-new"]
            cmd += [f"{user}@{host}", "sshd -T 2>/dev/null | grep authorizedkeysfile"]
            env["SSHPASS"] = password
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, env=env)
            for line in result.stdout.strip().splitlines():
                if "authorizedkeysfile" in line.lower():
                    path = line.split(None, 1)[-1].strip()
                    path = path.replace("%u", user).replace("~", f"/home/{user}")
                    return path
        except Exception:
            pass
        return None

    def _fix_authorized_keys_location(self, user, host, password, pub_key_path):
        auth_keys_path = self._detect_authorized_keys_path(user, host, password)
        if not auth_keys_path or auth_keys_path == f"/home/{user}/.ssh/authorized_keys":
            return
        self._output.append(f"\n🔧 Server uses AuthorizedKeysFile: {auth_keys_path}")
        self._output.append("   Copying key to correct location...")
        try:
            with open(pub_key_path) as f:
                pub_key = f.read().strip()
            remote_cmd = (
                f"mkdir -p $(dirname {auth_keys_path}) && "
                f"grep -qxF '{pub_key}' {auth_keys_path} 2>/dev/null || "
                f"echo '{pub_key}' >> {auth_keys_path} && "
                f"chmod 600 {auth_keys_path} && echo OK"
            )
            cmd = ["ssh", "-o", "StrictHostKeyChecking=accept-new", f"{user}@{host}", remote_cmd]
            env = os.environ.copy()
            if password:
                cmd = ["sshpass", "-e"] + ["ssh", "-o", "StrictHostKeyChecking=accept-new", f"{user}@{host}", remote_cmd]
                env["SSHPASS"] = password
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, env=env)
            if "OK" in result.stdout:
                self._output.append("✅ Key copied to correct location")
            else:
                self._output.append(f"⚠ Could not copy key: {result.stderr.strip()}")
        except Exception as e:
            self._output.append(f"⚠ Could not fix key location: {e}")

    def _push_key_to_server(self):
        import shutil

        user = self._push_user.text().strip()
        host = self._push_host.text().strip()
        key = self._push_key.text().strip()
        password = self._push_password.text()

        if not user or not host:
            QMessageBox.warning(self, "Error", "Username and host are required")
            return

        if not shutil.which("ssh-copy-id"):
            self._output.append("❌ ssh-copy-id not found. Install openssh-client: sudo apt install openssh-client")
            return

        if not shutil.which("sshpass"):
            self._output.append("❌ sshpass not found. Install: sudo apt install sshpass")
            return

        self._output.clear()
        self._output.append(f"Pushing key to {user}@{host}...\n")

        cmd = ["ssh-copy-id"]
        if key:
            if not os.path.exists(key):
                self._output.append(f"❌ Public key file not found: {key}")
                self._output.append("→ Generate a key first, or browse to select the .pub file")
                return
            cmd += ["-i", key]
        cmd += [
            "-o", "PreferredAuthentications=password,keyboard-interactive",
            "-o", "PubkeyAuthentication=no",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "IdentitiesOnly=yes",
            f"{user}@{host}",
        ]

        env = os.environ.copy()
        if password:
            cmd = ["sshpass", "-e"] + cmd
            env["SSHPASS"] = password

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
                env=env,
            )
            if result.stdout:
                self._output.append(result.stdout)
            if result.stderr:
                self._output.append(result.stderr)
            if result.returncode == 0:
                self._output.append(f"\n✅ Key copied to {user}@{host}")
                self._output.append("   Verifying key works...")
                if self._verify_key_auth(user, host, key, password):
                    self._output.append("✅ Key authentication verified!")
                    self._fix_authorized_keys_location(user, host, password, key)
                else:
                    self._output.append("⚠ Key does not work — server may not support this key type")
                    self._output.append("→ Retrying with RSA-4096...")
                    self._push_rsa_fallback(user, host, key, password)
            else:
                stderr_lower = result.stderr.lower() if result.stderr else ""
                if "denied" in stderr_lower or "authentication" in stderr_lower:
                    self._output.append(f"\n❌ ssh-copy-id failed (exit code {result.returncode})")
                    self._output.append("→ Wrong password or user rejected pubkey auth")
                elif "connection" in stderr_lower or "connect" in stderr_lower:
                    self._output.append(f"\n❌ ssh-copy-id failed (exit code {result.returncode})")
                    self._output.append("→ Cannot reach host — check IP/hostname and port 22")
                elif "no such file" in stderr_lower or "id file" in stderr_lower:
                    self._output.append(f"\n❌ ssh-copy-id failed (exit code {result.returncode})")
                    self._output.append("→ Key file not found — generate a key first")
                elif "already" in stderr_lower:
                    self._output.append(f"\n❌ ssh-copy-id failed (exit code {result.returncode})")
                    self._output.append("→ Key may already be installed")
                else:
                    self._output.append(f"\n❌ ssh-copy-id failed (exit code {result.returncode})")
        except Exception as e:
            self._output.append(f"Error: {e}")

    def _verify_key_auth(self, user, host, key, password):
        if not key:
            return True
        priv_key = key.replace(".pub", "") if key.endswith(".pub") else key
        if not os.path.exists(priv_key):
            return True
        cmd = [
            "ssh", "-i", priv_key,
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "IdentitiesOnly=yes",
            "-o", "PreferredAuthentications=publickey",
            f"{user}@{host}", "echo", "OK",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.returncode == 0 and "OK" in result.stdout
        except Exception:
            return True

    def _push_rsa_fallback(self, user, host, orig_key, password):
        import shutil
        rsa_key = os.path.expanduser("~/.ssh/id_rsa_fallback")
        rsa_pub = rsa_key + ".pub"
        try:
            self._output.append("   Generating RSA-4096 key...")
            result = subprocess.run(
                ["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", rsa_key, "-N", "", "-C", "fallback"],
                capture_output=True, text=True, timeout=30, input="y\n",
            )
            if result.returncode != 0:
                self._output.append(f"❌ Failed to generate RSA key: {result.stderr}")
                return
            self._output.append(f"   Generated: {rsa_key}")

            env = os.environ.copy()
            cmd = [
                "ssh-copy-id", "-i", rsa_pub,
                "-o", "PreferredAuthentications=password,keyboard-interactive",
                "-o", "PubkeyAuthentication=no",
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "IdentitiesOnly=yes",
                f"{user}@{host}",
            ]
            if password:
                cmd = ["sshpass", "-e"] + cmd
                env["SSHPASS"] = password
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
            if result.stdout:
                self._output.append(result.stdout)
            if result.stderr:
                self._output.append(result.stderr)
            if result.returncode == 0:
                self._output.append(f"\n✅ RSA key pushed to {user}@{host}")
                self._fix_authorized_keys_location(user, host, password, rsa_pub)
                self._push_key.setText(rsa_pub)
            else:
                self._output.append(f"\n❌ RSA push also failed")
        except Exception as e:
            self._output.append(f"❌ Fallback failed: {e}")

    def _center_on_parent(self):
        parent = self.parent()
        if parent:
            pw, ph = parent.width(), parent.height()
            px, py = parent.x(), parent.y()
            sw, sh = self.width(), self.height()
            self.move(px + (pw - sw) // 2, py + (ph - sh) // 2)
