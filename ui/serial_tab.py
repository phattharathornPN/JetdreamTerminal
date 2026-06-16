from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox
from PyQt6.QtCore import pyqtSignal, QTimer
from models.session import Session
from core.serial_client import SerialManager
from ui.terminal_widget import TerminalWidget
from utils.logger import log


class SerialTab(QWidget):
    closed = pyqtSignal(object)

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._serial = SerialManager(self)
        self._term = TerminalWidget(self)
        self._term.set_serial(self._serial)
        self._connecting = False
        self._setup_ui()
        self._serial.connection_lost.connect(self._on_disconnect)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 2, 4, 2)
        toolbar.setSpacing(4)

        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(200)
        self._port_combo.setMaximumHeight(26)
        self._port_combo.currentIndexChanged.connect(self._on_port_changed)
        self._refresh_ports()
        toolbar.addWidget(self._port_combo)

        self._refresh_btn = QPushButton("↻")
        self._refresh_btn.setFixedSize(26, 26)
        self._refresh_btn.setToolTip("Refresh ports")
        self._refresh_btn.clicked.connect(self._refresh_ports)
        toolbar.addWidget(self._refresh_btn)

        self._baud_combo = QComboBox()
        self._baud_combo.setFixedWidth(70)
        self._baud_combo.setMaximumHeight(26)
        self._baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        baud_idx = self._baud_combo.findText(str(self.session.baudrate))
        if baud_idx >= 0:
            self._baud_combo.setCurrentIndex(baud_idx)
        toolbar.addWidget(self._baud_combo)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setFixedHeight(26)
        self._connect_btn.clicked.connect(self._toggle_connect)
        toolbar.addWidget(self._connect_btn)

        self._status_label = QLabel("Disconnected")
        self._status_label.setStyleSheet("color: #bf616a; font-size: 11px;")
        self._status_label.setMaximumHeight(26)
        toolbar.addWidget(self._status_label)

        toolbar.addStretch()

        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar)
        toolbar_widget.setFixedHeight(32)
        toolbar_widget.setStyleSheet("background: #3b4252;")
        layout.addWidget(toolbar_widget)

        layout.addWidget(self._term)

    def _refresh_ports(self):
        import serial.tools.list_ports
        self._port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            desc = p.device
            if p.description and p.description != "n/a":
                desc += f" — {p.description}"
            self._port_combo.addItem(desc, p.device)
        if self.session.serial_port:
            idx = self._port_combo.findData(self.session.serial_port)
            if idx >= 0:
                self._port_combo.setCurrentIndex(idx)
            else:
                self._port_combo.setEditText(self.session.serial_port)

    def _toggle_connect(self):
        if self._serial.is_connected():
            self._serial.disconnect()
            self._connect_btn.setText("Connect")
            self._status_label.setText("Disconnected")
            self._status_label.setStyleSheet("color: #bf616a; font-size: 11px;")
        else:
            port = self._port_combo.currentData() or self._port_combo.currentText()
            baud = int(self._baud_combo.currentText())
            self.session.serial_port = port
            self.session.baudrate = baud
            self._serial.connect(port, baud)
            if self._serial.is_connected():
                self._connect_btn.setText("Disconnect")
                self._status_label.setText(f"Connected: {port} @ {baud}")
                self._status_label.setStyleSheet("color: #a3be8c; font-size: 11px;")
                self._term.setFocus()

    def _on_disconnect(self, reason: str):
        self._connect_btn.setText("Connect")
        self._status_label.setText(f"Lost: {reason}")
        self._status_label.setStyleSheet("color: #bf616a; font-size: 11px;")

    def _on_port_changed(self, index):
        if index >= 0 and self._serial.is_connected():
            self._serial.disconnect()
            self._connect_btn.setText("Connect")
            self._status_label.setText("Disconnected")
            self._status_label.setStyleSheet("color: #bf616a; font-size: 11px;")
            self._term.setFocus()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._serial.is_connected() and not self._connecting:
            self._connecting = True
            QTimer.singleShot(100, self._auto_connect)

    def _auto_connect(self):
        port = self.session.serial_port
        baud = self.session.baudrate
        if port:
            self._serial.connect(port, baud)
            if self._serial.is_connected():
                self._connect_btn.setText("Disconnect")
                self._status_label.setText(f"Connected: {port} @ {baud}")
                self._status_label.setStyleSheet("color: #a3be8c; padding: 4px;")
                self._term.setFocus()
        self._connecting = False

    def disconnect(self):
        if self._serial:
            self._serial.disconnect()
