from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QCheckBox, QPushButton,
    QLabel, QGroupBox, QFileDialog, QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from models.session import Session, SessionType, AuthType
from core.session_manager import save
from core.crypto import encrypt, decrypt
from utils.logger import log


class SessionDialog(QDialog):
    session_saved = pyqtSignal(Session)

    def __init__(self, session: Session | None = None, parent=None):
        super().__init__(parent)
        self.session = session or Session()
        self._is_edit = session is not None and session.id > 0
        self.setWindowTitle("Edit Session" if self._is_edit else "New Session")
        self.setMinimumWidth(450)
        self.setMinimumHeight(500)
        self._setup_ui()
        self._center_on_parent()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self._name = QLineEdit(self.session.name)
        self._name_label = QLabel("Name:")
        form.addRow(self._name_label, self._name)

        self._type = QComboBox()
        self._type.addItems(["SSH", "Telnet", "RDP", "SFTP", "Serial", "VPN", "VNC"])
        type_map = {
            SessionType.SSH: 0, SessionType.TELNET: 1, SessionType.RDP: 2,
            SessionType.SFTP: 3, SessionType.SERIAL: 4, SessionType.VPN: 5,
            SessionType.VNC: 6,
        }
        self._type.setCurrentIndex(type_map.get(self.session.session_type, 0))
        self._type.currentIndexChanged.connect(self._on_type_changed)
        self._type_label = QLabel("Type:")
        form.addRow(self._type_label, self._type)

        self._host = QLineEdit(self.session.host)
        self._host_label = QLabel("Host:")
        form.addRow(self._host_label, self._host)

        self._port = QLineEdit(str(self.session.port))
        self._port_label = QLabel("Port:")
        form.addRow(self._port_label, self._port)

        self._username = QLineEdit(self.session.username)
        self._username_label = QLabel("Username:")
        form.addRow(self._username_label, self._username)

        self._auth = QComboBox()
        self._auth.addItems(["Password", "Key", "Key + Password", "None"])
        auth_map = {
            AuthType.PASSWORD: 0, AuthType.KEY: 1,
            AuthType.KEY_WITH_PASSWORD: 2, AuthType.NONE: 3,
        }
        self._auth.setCurrentIndex(auth_map.get(self.session.auth_type, 0))
        self._auth.currentIndexChanged.connect(self._on_auth_changed)
        self._auth_label = QLabel("Auth:")
        form.addRow(self._auth_label, self._auth)

        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        if self.session.password_encrypted:
            try:
                self._password.setText(decrypt(self.session.password_encrypted))
            except Exception:
                pass
        self._password_label = QLabel("Password:")
        form.addRow(self._password_label, self._password)

        self._key_layout = QHBoxLayout()
        self._key_path = QLineEdit(self.session.key_path)
        self._key_browse = QPushButton("Browse")
        self._key_browse.clicked.connect(self._browse_key)
        self._key_layout.addWidget(self._key_path)
        self._key_layout.addWidget(self._key_browse)
        self._key_widget = QWidget()
        self._key_widget.setLayout(self._key_layout)
        self._key_label = QLabel("Key file:")
        form.addRow(self._key_label, self._key_widget)

        self._legacy = QCheckBox("Legacy device mode (Cisco 2960X/Aruba)")
        self._legacy.setChecked(self.session.legacy_mode)
        form.addRow("", self._legacy)

        self._vpn_realm = QLineEdit(self.session.vpn_realm)
        self._vpn_realm.setPlaceholderText("(optional)")
        self._vpn_realm_label = QLabel("VPN Realm:")
        form.addRow(self._vpn_realm_label, self._vpn_realm)

        self._vpn_cert = QLineEdit(self.session.vpn_trusted_cert)
        self._vpn_cert.setPlaceholderText("sha256 hash from error message")
        self._vpn_cert_label = QLabel("Trusted Cert:")
        form.addRow(self._vpn_cert_label, self._vpn_cert)

        self._vnc_port = QLineEdit(str(self.session.vnc_port or 5900))
        self._vnc_port_label = QLabel("VNC Port:")
        form.addRow(self._vnc_port_label, self._vnc_port)

        self._serial_port_layout = QHBoxLayout()
        self._serial_port = QComboBox()
        self._serial_port.setEditable(True)
        self._serial_port.setMinimumWidth(200)
        self._serial_refresh = QPushButton("↻")
        self._serial_refresh.setMaximumWidth(30)
        self._serial_refresh.setToolTip("Refresh serial ports")
        self._serial_refresh.clicked.connect(self._refresh_serial_ports)
        self._serial_port_layout.addWidget(self._serial_port)
        self._serial_port_layout.addWidget(self._serial_refresh)
        self._serial_port_widget = QWidget()
        self._serial_port_widget.setLayout(self._serial_port_layout)
        self._serial_port_label = QLabel("Serial Port *:")
        form.addRow(self._serial_port_label, self._serial_port_widget)

        self._baudrate = QComboBox()
        self._baudrate.addItems(["9600", "19200", "38400", "57600", "115200"])
        baud_idx = self._baudrate.findText(str(self.session.baudrate))
        if baud_idx >= 0:
            self._baudrate.setCurrentIndex(baud_idx)
        self._baudrate_label = QLabel("Baudrate:")
        form.addRow(self._baudrate_label, self._baudrate)

        self._serial_info = QLabel("")
        self._serial_info.setStyleSheet("color: #88c0d0; padding: 4px;")
        self._serial_info.setWordWrap(True)
        form.addRow("", self._serial_info)

        self._group = QLineEdit(self.session.group)
        self._group_label = QLabel("Group:")
        form.addRow(self._group_label, self._group)

        self._favorite = QCheckBox("Favorite (⭐ pin to top)")
        self._favorite.setChecked(self.session.favorite)
        form.addRow("", self._favorite)

        self._auto_save = QCheckBox("Auto-save output on close")
        self._auto_save.setChecked(self.session.auto_save)
        form.addRow("", self._auto_save)

        layout.addLayout(form)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self._on_save)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._save_btn)
        layout.addLayout(btn_layout)

        self._on_type_changed()
        self._refresh_serial_ports()

    def _refresh_serial_ports(self):
        self._serial_port.clear()
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            if ports:
                for p in ports:
                    desc = f"{p.device}"
                    if p.description and p.description != "n/a":
                        desc += f" — {p.description}"
                    self._serial_port.addItem(desc, p.device)
                self._serial_info.setText(f"Found {len(ports)} port(s)")
            else:
                self._serial_port.addItem("No ports found", "")
                self._serial_info.setText("No serial ports detected — plug in USB-to-Serial adapter")
        except ImportError:
            self._serial_port.addItem("pyserial not installed", "")
            self._serial_info.setText("Install: pip install pyserial")

        if self.session.serial_port:
            idx = self._serial_port.findData(self.session.serial_port)
            if idx >= 0:
                self._serial_port.setCurrentIndex(idx)
            else:
                self._serial_port.setEditText(self.session.serial_port)

    def _on_type_changed(self):
        idx = self._type.currentIndex()
        is_rdp = idx == 2
        is_serial = idx == 4
        is_ssh = idx == 0
        is_telnet = idx == 1
        is_sftp = idx == 3
        is_vpn = idx == 5
        is_vnc = idx == 6
        is_network = is_ssh or is_telnet or is_sftp or is_rdp or is_serial or is_vpn or is_vnc

        self._host.setVisible(is_network)
        self._host_label.setVisible(is_network)
        self._port.setVisible(is_network)
        self._port_label.setVisible(is_network)
        self._username.setVisible(is_network and not is_serial and not is_vpn and not is_vnc)
        self._username_label.setVisible(is_network and not is_serial and not is_vpn and not is_vnc)
        self._auth.setVisible(is_network and not is_serial and not is_rdp and not is_vpn and not is_vnc)
        self._auth_label.setVisible(is_network and not is_serial and not is_rdp and not is_vpn and not is_vnc)
        self._password.setVisible(is_network and not is_serial and not is_vpn and not is_vnc)
        self._password_label.setVisible(is_network and not is_serial and not is_vpn and not is_vnc)
        self._serial_port_widget.setVisible(is_serial)
        self._serial_port_label.setVisible(is_serial)
        self._baudrate.setVisible(is_serial)
        self._baudrate_label.setVisible(is_serial)
        self._serial_info.setVisible(is_serial)
        self._legacy.setVisible(is_ssh or is_telnet)

        self._vpn_realm.setVisible(is_vpn)
        self._vpn_realm_label.setVisible(is_vpn)
        self._vpn_cert.setVisible(is_vpn)
        self._vpn_cert_label.setVisible(is_vpn)

        self._vnc_port.setVisible(is_vnc)
        self._vnc_port_label.setVisible(is_vnc)

        self._host.setEnabled(True)
        self._port.setEnabled(True)
        self._username.setEnabled(True)
        self._auth.setEnabled(not is_rdp)
        self._key_widget.setEnabled(not is_rdp)

        default_ports = {0: "22", 1: "23", 2: "3389", 3: "22", 4: "0", 5: "443", 6: "5901"}
        self._port.setText(default_ports.get(idx, "22"))

        for w in (self._name, self._host, self._port, self._username, self._password):
            w.setStyleSheet("")
        self._serial_port.setStyleSheet("")

        REQUIRED = "border: 2px solid #bf616a; border-radius: 3px; background: #3b2025;"
        OPTIONAL = "border: 1px solid #4c566a; border-radius: 3px;"

        self._host_label.setText("Host:")
        self._port_label.setText("Port:")
        self._username_label.setText("Username:")
        self._password_label.setText("Password:")
        self._serial_port_label.setText("Serial Port:")

        if is_ssh:
            self._host_label.setText("Host *:")
            self._username_label.setText("Username *:")
            self._host.setStyleSheet(REQUIRED)
            self._port.setStyleSheet(OPTIONAL)
            self._username.setStyleSheet(REQUIRED)
            self._update_auth_styles()
        elif is_telnet:
            self._host_label.setText("Host *:")
            self._host.setStyleSheet(REQUIRED)
            self._port.setStyleSheet(OPTIONAL)
        elif is_sftp:
            self._host_label.setText("Host *:")
            self._username_label.setText("Username *:")
            self._host.setStyleSheet(REQUIRED)
            self._port.setStyleSheet(OPTIONAL)
            self._username.setStyleSheet(REQUIRED)
            self._update_auth_styles()
        elif is_serial:
            self._serial_port_label.setText("Serial Port *:")
            self._serial_port.setStyleSheet(REQUIRED)
        elif is_vpn:
            self._host_label.setText("VPN Host *:")
            self._port_label.setText("Port:")
            self._host.setStyleSheet(REQUIRED)
            self._port.setStyleSheet(OPTIONAL)
            self._vpn_realm_label.setText("Realm:")
            self._vpn_realm.setStyleSheet(OPTIONAL)
            self._vpn_cert_label.setText("Trusted Cert:")
            self._vpn_cert.setStyleSheet(OPTIONAL)

        self._on_auth_changed()

    def _on_auth_changed(self):
        idx = self._auth.currentIndex()
        has_password = idx in (0, 2)
        has_key = idx in (1, 2)
        is_serial = self._type.currentIndex() == 4
        is_rdp = self._type.currentIndex() == 2
        self._password.setVisible(has_password)
        self._password_label.setVisible(has_password)
        self._key_widget.setVisible(has_key and not is_serial and not is_rdp)
        self._key_label.setVisible(has_key and not is_serial and not is_rdp)
        self._update_auth_styles()

    def _update_auth_styles(self):
        REQUIRED = "border: 2px solid #bf616a; border-radius: 3px; background: #3b2025;"
        OPTIONAL = "border: 1px solid #4c566a; border-radius: 3px;"
        auth_idx = self._auth.currentIndex()
        needs_password = auth_idx in (0, 2)
        self._password_label.setText("Password:" if not needs_password else "Password *:")
        self._password.setStyleSheet(REQUIRED if needs_password else OPTIONAL)
        self._key_label.setText("Key file:")
        self._key_widget.setStyleSheet(OPTIONAL)

    def _browse_key(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select SSH Key", "",
            "SSH Keys (*.pub *.pem);;All Files (*)"
        )
        if path:
            self._key_path.setText(path)

    def _on_save(self):
        self.session.name = self._name.text().strip()
        type_vals = [SessionType.SSH, SessionType.TELNET, SessionType.RDP,
                     SessionType.SFTP, SessionType.SERIAL, SessionType.VPN,
                     SessionType.VNC]
        self.session.session_type = type_vals[self._type.currentIndex()]
        self.session.host = self._host.text().strip()
        try:
            self.session.port = int(self._port.text())
        except ValueError:
            self.session.port = 22
        self.session.username = self._username.text().strip()
        auth_vals = [AuthType.PASSWORD, AuthType.KEY,
                     AuthType.KEY_WITH_PASSWORD, AuthType.NONE]
        self.session.auth_type = auth_vals[self._auth.currentIndex()]
        self.session.legacy_mode = self._legacy.isChecked()
        serial_data = self._serial_port.currentData()
        if serial_data:
            self.session.serial_port = serial_data
        else:
            self.session.serial_port = self._serial_port.currentText().strip()
        try:
            self.session.baudrate = int(self._baudrate.currentText())
        except ValueError:
            self.session.baudrate = 9600
        self.session.group = self._group.text().strip() or "Default"
        self.session.key_path = self._key_path.text().strip()
        self.session.favorite = self._favorite.isChecked()
        self.session.auto_save = self._auto_save.isChecked()
        self.session.vpn_realm = self._vpn_realm.text().strip()
        self.session.vpn_trusted_cert = self._vpn_cert.text().strip()
        try:
            self.session.vnc_port = int(self._vnc_port.text())
        except ValueError:
            self.session.vnc_port = 5900

        pw = self._password.text()
        if pw:
            self.session.password_encrypted = encrypt(pw)
        elif not self._is_edit:
            self.session.password_encrypted = b""

        session_id = save(self.session)
        self.session.id = session_id
        self.session_saved.emit(self.session)
        self.accept()

    def _center_on_parent(self):
        parent = self.parent()
        if parent:
            pw, ph = parent.width(), parent.height()
            px, py = parent.x(), parent.y()
            sw, sh = self.width(), self.height()
            self.move(px + (pw - sw) // 2, py + (ph - sh) // 2)
