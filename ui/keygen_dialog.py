import os
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QTextEdit, QFileDialog,
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

        self._key_type = QLineEdit("ed25519")
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

    def _generate_key(self):
        key_type = self._key_type.text().strip() or "ed25519"
        comment = self._key_comment.text().strip()
        key_file = self._key_file.text().strip() or os.path.expanduser(f"~/.ssh/id_{key_type}")

        if os.path.exists(key_file):
            reply = QMessageBox.question(
                self, "Overwrite?",
                f"Key file already exists:\n{key_file}\n\nOverwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        cmd = ["ssh-keygen", "-t", key_type, "-f", key_file, "-N", ""]
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
        except Exception as e:
            self._output.append(f"Error: {e}")

    def _push_key_to_server(self):
        user = self._push_user.text().strip()
        host = self._push_host.text().strip()
        key = self._push_key.text().strip()
        password = self._push_password.text()

        if not user or not host:
            QMessageBox.warning(self, "Error", "Username and host are required")
            return

        cmd = ["ssh-copy-id"]
        if key:
            cmd += ["-i", key]
        cmd.append(f"{user}@{host}")

        if password:
            cmd = ["sshpass", "-p", password] + cmd

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
            )
            self._output.append(result.stdout)
            if result.stderr:
                self._output.append(result.stderr)
            if result.returncode == 0:
                self._output.append(f"\n✅ Key pushed to {user}@{host}")
            else:
                self._output.append(f"\n❌ Failed (exit code {result.returncode})")
        except FileNotFoundError:
            self._output.append("❌ sshpass not found. Install: sudo apt install sshpass")
        except Exception as e:
            self._output.append(f"Error: {e}")

    def _center_on_parent(self):
        parent = self.parent()
        if parent:
            pw, ph = parent.width(), parent.height()
            px, py = parent.x(), parent.y()
            sw, sh = self.width(), self.height()
            self.move(px + (pw - sw) // 2, py + (ph - sh) // 2)
