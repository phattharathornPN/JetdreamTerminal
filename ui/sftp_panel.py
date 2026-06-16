from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QFileDialog, QLineEdit, QHeaderView, QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QColor
from models.session import Session
from core.sftp_browser import SftpBrowser
from core.crypto import decrypt
from utils.logger import log


class SftpWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, sftp: SftpBrowser, path: str):
        super().__init__()
        self.sftp = sftp
        self.path = path

    def run(self):
        try:
            items = self.sftp.list_dir(self.path)
            self.finished.emit(items)
        except Exception as e:
            self.error.emit(str(e))


class SftpTransfer(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, browser: SftpBrowser, direction: str, src: str, dst: str):
        super().__init__()
        self.browser = browser
        self.direction = direction
        self.src = src
        self.dst = dst

    def run(self):
        try:
            if self.direction == "download":
                self.browser.download(self.src, self.dst)
                self.finished.emit(f"Downloaded: {self.src}")
            else:
                self.browser.upload(self.src, self.dst)
                self.finished.emit(f"Uploaded: {self.src}")
        except Exception as e:
            self.error.emit(str(e))


class SftpPanel(QWidget):
    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._browser = SftpBrowser(session)
        self._current_path = "."
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        self._path_edit = QLineEdit(".")
        self._path_edit.setPlaceholderText("Remote path")
        self._path_edit.returnPressed.connect(self._navigate)
        toolbar.addWidget(self._path_edit)

        self._up_btn = QPushButton("⬆")
        self._up_btn.setFixedSize(28, 28)
        self._up_btn.setToolTip("Go up")
        self._up_btn.clicked.connect(self._go_up)
        toolbar.addWidget(self._up_btn)

        self._refresh_btn = QPushButton("↻")
        self._refresh_btn.setFixedSize(28, 28)
        self._refresh_btn.setToolTip("Refresh")
        self._refresh_btn.clicked.connect(self._navigate)
        toolbar.addWidget(self._refresh_btn)

        self._retry_btn = QPushButton("🔄 Retry")
        self._retry_btn.setFixedHeight(28)
        self._retry_btn.setToolTip("Reconnect SFTP")
        self._retry_btn.clicked.connect(self.connect_sftp)
        toolbar.addWidget(self._retry_btn)

        toolbar.addStretch()

        self._upload_btn = QPushButton("⬆ Upload")
        self._upload_btn.clicked.connect(self._upload)
        toolbar.addWidget(self._upload_btn)

        self._download_btn = QPushButton("⬇ Download")
        self._download_btn.clicked.connect(self._download)
        toolbar.addWidget(self._download_btn)

        layout.addLayout(toolbar)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Name", "Size", "Permissions"])
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        header = self._tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._tree)

        self._status = QLabel("Disconnected")
        self._status.setStyleSheet("color: #bf616a; font-size: 11px; padding: 2px;")
        layout.addWidget(self._status)

    def connect_sftp(self):
        password = ""
        if self.session.password_encrypted:
            try:
                password = decrypt(self.session.password_encrypted)
            except Exception:
                pass
        try:
            self._browser.connect(password)
            self._status.setText(f"Connected: {self.session.username}@{self.session.host}")
            self._status.setStyleSheet("color: #a3be8c; font-size: 11px; padding: 2px;")
            self._path_edit.setText("~")
            self._navigate()
        except Exception as e:
            self._status.setText(f"❌ {e}")
            self._status.setStyleSheet("color: #bf616a; font-size: 11px; padding: 2px;")
            log.error(f"SFTP connect failed: {e}")

    def _navigate(self):
        path = self._path_edit.text().strip() or "~"
        self._current_path = path
        self._tree.clear()
        self._worker = SftpWorker(self._browser, path)
        self._worker.finished.connect(self._on_items)
        self._worker.error.connect(lambda e: (
            self._status.setText(f"Error: {e}"),
            self._status.setStyleSheet("color: #bf616a; font-size: 11px; padding: 2px;")
        ))
        self._worker.start()

    def _on_items(self, items: list[dict]):
        for item in items:
            perm = oct(item["permissions"])[-3:] if item["permissions"] else "---"
            twi = QTreeWidgetItem([
                item["name"],
                self._format_size(item["size"]),
                perm,
            ])
            twi.setData(0, Qt.ItemDataRole.UserRole, item)
            if item["is_dir"]:
                twi.setForeground(0, QColor("#88c0d0"))
                twi.setText(1, "")
            self._tree.addTopLevelItem(twi)
        self._status.setText(f"{self._current_path} — {len(items)} items")

    def _on_double_click(self, item: QTreeWidgetItem, col: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("is_dir"):
            name = data["name"]
            if name == "..":
                self._go_up()
            else:
                base = self._current_path.replace("\\", "/").rstrip("/")
                new_path = f"{base}/{name}"
                self._path_edit.setText(new_path)
                self._navigate()

    def _go_up(self):
        parts = self._current_path.replace("\\", "/").rsplit("/", 1)
        if len(parts) > 1:
            parent = parts[0] or "/"
        else:
            parent = "/"
        self._path_edit.setText(parent)
        self._navigate()

    def _upload(self):
        local_path, _ = QFileDialog.getOpenFileName(self, "Select file to upload")
        if not local_path:
            return
        import os
        filename = os.path.basename(local_path)
        base = self._current_path.replace("\\", "/").rstrip("/")
        remote_path = f"{base}/{filename}"
        self._status.setText(f"Uploading {filename}...")
        self._worker = SftpTransfer(self._browser, "upload", local_path, remote_path)
        self._worker.finished.connect(self._on_transfer_done)
        self._worker.error.connect(lambda e: self._status.setText(f"Error: {e}"))
        self._worker.start()

    def _download(self):
        items = self._tree.selectedItems()
        if not items:
            self._status.setText("Select a file to download")
            return
        for item in items:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if not data or data.get("is_dir"):
                continue
            base = self._current_path.replace("\\", "/").rstrip("/")
            remote_path = f"{base}/{data['name']}"
            local_path, _ = QFileDialog.getSaveFileName(
                self, f"Save {data['name']}", data['name']
            )
            if not local_path:
                continue
            self._status.setText(f"Downloading {data['name']}...")
            self._worker = SftpTransfer(self._browser, "download", remote_path, local_path)
            self._worker.finished.connect(self._on_transfer_done)
            self._worker.error.connect(lambda e: self._status.setText(f"Error: {e}"))
            self._worker.start()

    def _on_transfer_done(self, msg: str):
        self._status.setText(f"✅ {msg}")
        self._status.setStyleSheet("color: #a3be8c; font-size: 11px; padding: 2px;")
        self._navigate()

    def _format_size(self, size: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def disconnect(self):
        self._browser.disconnect()
