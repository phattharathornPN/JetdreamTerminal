import serial
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from utils.logger import log


class SerialManager(QObject):
    data_received = pyqtSignal(bytes)
    connection_lost = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._serial: serial.Serial | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)

    def connect(self, port: str, baudrate: int = 9600):
        self.disconnect()
        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0,
            )
            log.info(f"Serial connected: {port} @ {baudrate}")
            self._timer.start(10)
        except serial.SerialException as e:
            log.error(f"Serial connect failed: {e}")
            self.connection_lost.emit(str(e))

    def _poll(self):
        if not self._serial or not self._serial.is_open:
            self._timer.stop()
            return
        try:
            data = self._serial.read(4096)
            if data:
                self.data_received.emit(data)
        except serial.SerialException as e:
            log.error(f"Serial read error: {e}")
            self.connection_lost.emit(str(e))
            self._timer.stop()

    def write(self, data: bytes):
        if self._serial and self._serial.is_open:
            try:
                self._serial.write(data)
            except serial.SerialException as e:
                log.error(f"Serial write error: {e}")

    def disconnect(self):
        self._timer.stop()
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
            log.info("Serial disconnected")

    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open
