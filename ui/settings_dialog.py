import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QSlider,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from ui.theme import (
    get_terminal_bg_image, set_terminal_bg_image,
    get_terminal_opacity, set_terminal_opacity,
)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self._setup_ui()
        self._center_on_parent()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        bg_group = QLabel("Terminal Background Image")
        bg_group.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px 0;")
        layout.addWidget(bg_group)

        img_layout = QHBoxLayout()

        self._preview = QLabel()
        self._preview.setFixedSize(200, 120)
        self._preview.setStyleSheet("border: 1px solid #4c566a; background: #2e3440;")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_layout.addWidget(self._preview)

        img_right = QVBoxLayout()

        self._img_path = QLabel(get_terminal_bg_image() or "No image selected")
        self._img_path.setStyleSheet("color: #a5adba; font-size: 11px;")
        self._img_path.setWordWrap(True)
        img_right.addWidget(self._img_path)

        btn_row = QHBoxLayout()
        self._browse_btn = QPushButton("Browse...")
        self._browse_btn.clicked.connect(self._browse_image)
        btn_row.addWidget(self._browse_btn)

        self._clear_btn = QPushButton("Remove")
        self._clear_btn.clicked.connect(self._clear_image)
        btn_row.addWidget(self._clear_btn)
        img_right.addLayout(btn_row)

        img_layout.addLayout(img_right)
        img_layout.addStretch()
        layout.addLayout(img_layout)

        self._update_preview()

        layout.addSpacing(16)

        opacity_label = QLabel("Background Opacity")
        opacity_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px 0;")
        layout.addWidget(opacity_label)

        opacity_layout = QHBoxLayout()
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(10, 100)
        current_opacity = int(get_terminal_opacity() * 100)
        self._opacity_slider.setValue(current_opacity)
        self._opacity_slider.valueChanged.connect(self._on_opacity_change)
        opacity_layout.addWidget(self._opacity_slider)

        self._opacity_label = QLabel(f"{current_opacity}%")
        self._opacity_label.setFixedWidth(40)
        opacity_layout.addWidget(self._opacity_label)
        layout.addLayout(opacity_layout)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)
        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self._save)
        btn_layout.addWidget(self._save_btn)
        layout.addLayout(btn_layout)

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", os.path.expanduser("~"),
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if path:
            set_terminal_bg_image(path)
            self._img_path.setText(path)
            self._update_preview()

    def _clear_image(self):
        set_terminal_bg_image("")
        self._img_path.setText("No image selected")
        self._preview.clear()
        self._preview.setText("No image")

    def _on_opacity_change(self, val: int):
        self._opacity_label.setText(f"{val}%")

    def _update_preview(self):
        path = get_terminal_bg_image()
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            self._preview.setPixmap(
                pixmap.scaled(200, 120, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
            )
        else:
            self._preview.setText("No image")

    def _save(self):
        opacity = self._opacity_slider.value() / 100.0
        set_terminal_opacity(opacity)
        self.accept()

    def _center_on_parent(self):
        parent = self.parent()
        if parent:
            pw, ph = parent.width(), parent.height()
            px, py = parent.x(), parent.y()
            sw, sh = self.width(), self.height()
            self.move(px + (pw - sw) // 2, py + (ph - sh) // 2)
