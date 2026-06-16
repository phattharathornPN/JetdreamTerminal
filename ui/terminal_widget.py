import pyte
import os
import unicodedata
from datetime import datetime
from utils.logger import log
from PyQt6.QtWidgets import QWidget, QMenu, QApplication, QFileDialog, QLabel
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import (QPainter, QFont, QFontMetrics, QColor, QPen,
                         QKeyEvent, QAction, QMouseEvent, QWheelEvent, QPixmap)
from ui.theme import (get_terminal_bg, get_terminal_fg, get_terminal_bg_image,
                       get_terminal_opacity)
from ui.highlight import get_highlight_rules


class CopyToast(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background: #a3be8c; color: #2e3440; font-size: 12px; "
            "font-weight: bold; border-radius: 6px; padding: 6px 16px;"
        )
        self.setFixedHeight(28)
        self.hide()

    def show_toast(self, text: str):
        self.setText(text)
        self.adjustSize()
        if self.parent():
            pw = self.parent().width()
            self.move((pw - self.width()) // 2, 4)
        self.show()
        self.raise_()
        QTimer.singleShot(1500, self.hide)


class ThaiScreen(pyte.Screen):
    def draw(self, char: str):
        for ch in char:
            cat = unicodedata.category(ch)
            if cat.startswith('M') and self.cursor.x > 0:
                prev_x = self.cursor.x - 1
                row = self.buffer.get(self.cursor.y, {})
                prev = row.get(prev_x)
                if prev is not None:
                    row[prev_x] = prev._replace(data=prev.data + ch)
                    continue
            super().draw(ch)


class TerminalWidget(QWidget):
    save_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(True)
        self._font = QFont("JetBrains Mono", 13)
        self._font.setStyleHint(QFont.StyleHint.Monospace)
        self._font.setWeight(QFont.Weight.Bold)
        self._fm = QFontMetrics(self._font)
        self._cell_w = max(1, self._fm.averageCharWidth())
        self._cell_h = max(1, self._fm.height())

        self._cols = 80
        self._vis_rows = 24
        self._buf_rows = self._vis_rows + 5000
        self._screen = ThaiScreen(self._cols, self._buf_rows)
        self._stream = pyte.Stream(self._screen)
        self._byte_buffer = b""

        self._pty = None
        self._serial = None
        self._scroll_off = 0

        self._sb_dragging = False
        self._sb_drag_start_y = 0
        self._sb_drag_start_off = 0

        self._sel_start: QPoint | None = None
        self._sel_end: QPoint | None = None
        self._selecting = False
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.timeout.connect(self._auto_scroll_tick)
        self._auto_scroll_dir = 0

        self._toast = CopyToast(self)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._ansi_colors = {
            "0": "#1a1a2e", "1": "#ff5555", "2": "#50fa7b", "3": "#f1fa8c",
            "4": "#6272a4", "5": "#ff79c6", "6": "#8be9fd", "7": "#f8f8f2",
            "8": "#6272a4", "9": "#ff6e6e", "10": "#69ff94", "11": "#ffffa5",
            "12": "#6c71ff", "13": "#ff92df", "14": "#a4ffff", "15": "#ffffff",
        }
        self._default_bg = QColor(get_terminal_bg())
        self._default_fg = QColor(get_terminal_fg())
        self._sel_bg = QColor("#5e81ac")
        self._sel_fg = QColor("#ffffff")
        self._margin_x = 8
        self._margin_y = 4
        self._bg_pixmap: QPixmap | None = None
        self._bg_image_path = ""
        self._load_bg_image()

    def set_pty(self, pty_manager):
        self._pty = pty_manager
        pty_manager.data_received.connect(self._on_data)
        pty_manager.process_exited.connect(self._on_exit)

    def set_serial(self, serial_manager):
        self._serial = serial_manager
        serial_manager.data_received.connect(self._on_data)

    def _on_data(self, data: bytes):
        self._byte_buffer += data
        try:
            text = self._byte_buffer.decode('utf-8')
            self._byte_buffer = b""
        except UnicodeDecodeError:
            for i in range(len(self._byte_buffer), 0, -1):
                try:
                    text = self._byte_buffer[:i].decode('utf-8')
                    self._byte_buffer = self._byte_buffer[i:]
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return
        cursor_before = self._screen.cursor.y if self._screen.cursor else 0
        try:
            self._stream.feed(text)
        except Exception as e:
            log.error(f"pyte feed error: {e}")
        cursor_after = self._screen.cursor.y if self._screen.cursor else 0
        if self._scroll_off > 0:
            self._scroll_off += cursor_after - cursor_before
        self.update()

    def _get_top_row(self) -> int:
        cursor_y = self._screen.cursor.y if self._screen.cursor else 0
        return max(0, cursor_y - self._vis_rows + 1)

    def _get_display_line(self, row: int) -> list | None:
        top = self._get_top_row() - self._scroll_off
        buf_y = top + row
        if buf_y < 0 or buf_y >= self._buf_rows:
            return None
        raw = self._screen.buffer.get(buf_y, {})
        return [raw.get(x) for x in range(self._screen.columns)]

    def _cell_from_pos(self, pos: QPoint) -> QPoint:
        x = max(0, min((pos.x() - self._margin_x) // self._cell_w, self._cols - 1))
        y = max(0, min((pos.y() - self._margin_y) // self._cell_h, self._vis_rows - 1))
        return QPoint(x, y)

    def _get_sel_bounds(self):
        if not self._sel_start or not self._sel_end:
            return None
        sx = min(self._sel_start.x(), self._sel_end.x())
        ex = max(self._sel_start.x(), self._sel_end.x())
        sy = min(self._sel_start.y(), self._sel_end.y())
        ey = max(self._sel_start.y(), self._sel_end.y())
        return sx, ex, sy, ey

    def _get_selected_text(self) -> str:
        b = self._get_sel_bounds()
        if not b:
            return ""
        sx, ex, sy, ey = b
        lines = []
        for y in range(sy, ey + 1):
            cells = self._get_display_line(y)
            if cells is None:
                continue
            x1 = sx if y == sy else 0
            x2 = ex if y == ey else self._cols - 1
            line = ""
            for x in range(x1, min(x2 + 1, len(cells))):
                cell = cells[x]
                line += cell.data if cell and cell.data else " "
            lines.append(line.rstrip())
        return "\n".join(lines)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        has_sel = self._sel_start is not None and self._sel_end is not None

        copy_action = QAction("Copy Selection" if has_sel else "Copy All (Ctrl+Shift+C)", self)
        copy_action.triggered.connect(self._copy)
        menu.addAction(copy_action)

        paste_action = QAction("Paste (Ctrl+Shift+V)", self)
        paste_action.triggered.connect(self._paste)
        menu.addAction(paste_action)

        menu.addSeparator()

        save_action = QAction("Save Output...", self)
        save_action.triggered.connect(self._save_output)
        menu.addAction(save_action)

        clear_action = QAction("Clear Scrollback", self)
        clear_action.triggered.connect(self._clear)
        menu.addAction(clear_action)

        menu.exec(self.mapToGlobal(pos))

    def _copy(self):
        if self._sel_start and self._sel_end:
            text = self._get_selected_text()
        else:
            text = self.get_all_text()
        if text.strip():
            QApplication.clipboard().setText(text)
            n = text.count("\n") + 1
            self._toast.show_toast(f"Copied {n} line(s)")

    def _paste(self):
        text = QApplication.clipboard().text()
        if text:
            data = text.encode("utf-8")
            if self._pty:
                self._pty.write(data)
            elif self._serial:
                self._serial.write(data)

    def _save_output(self):
        default_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Terminal Output",
            os.path.expanduser(f"~/Desktop/{default_name}"),
            "Text Files (*.txt);;All Files (*)"
        )
        if path:
            text = self.get_all_text()
            with open(path, "w") as f:
                f.write(text)
            log.info(f"Output saved: {path}")

    def _clear(self):
        self._scroll_off = 0
        self._sel_start = None
        self._sel_end = None
        self._screen.reset()
        self.update()

    def _on_exit(self, code: int):
        self.update()

    def auto_save_output(self, session_name: str = "session"):
        try:
            text = self.get_all_text()
            if text.strip():
                save_dir = os.path.expanduser("~/JetdreamTerminal-logs")
                os.makedirs(save_dir, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = os.path.join(save_dir, f"{session_name}_{ts}.txt")
                with open(path, "w") as f:
                    f.write(text)
                log.info(f"Auto-saved output: {path}")
        except Exception as e:
            log.error(f"Auto-save failed: {e}")

    def _load_bg_image(self):
        path = get_terminal_bg_image()
        if path and os.path.exists(path) and path != self._bg_image_path:
            self._bg_pixmap = QPixmap(path)
            self._bg_image_path = path
        elif not path:
            self._bg_pixmap = None
            self._bg_image_path = ""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(self._font)
        painter.setOpacity(get_terminal_opacity())

        if self._bg_pixmap and not self._bg_pixmap.isNull():
            scaled = self._bg_pixmap.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.fillRect(self.rect(), self._default_bg)

        painter.setOpacity(1.0)

        b = self._get_sel_bounds()
        has_sel = b is not None
        if b:
            sx, ex, sy, ey = b

        at_bottom = self._scroll_off == 0

        rules = get_highlight_rules()

        for y in range(self._vis_rows):
            py = self._margin_y + y * self._cell_h
            cells = self._get_display_line(y)

            is_in_sel = has_sel and sy <= y <= ey

            if is_in_sel:
                is_single = sy == ey
                if is_single:
                    x1 = self._margin_x + sx * self._cell_w
                    w = (ex - sx + 1) * self._cell_w
                elif y == sy:
                    x1 = self._margin_x + sx * self._cell_w
                    w = self.width() - x1
                elif y == ey:
                    x1 = self._margin_x
                    w = (ex + 1) * self._cell_w
                else:
                    x1 = self._margin_x
                    w = self.width() - self._margin_x
                painter.fillRect(x1, py, w, self._cell_h, self._sel_bg)
                painter.fillRect(self._margin_x - 3, py, 3, self._cell_h, QColor("#88c0d0"))

            if cells is None:
                continue

            line_text = ""
            for x in range(min(self._cols, len(cells))):
                cell = cells[x]
                line_text += cell.data if cell and cell.data else " "

            hl_spans = []
            if not is_in_sel:
                for rule in rules:
                    for m in rule.pattern.finditer(line_text):
                        hl_spans.append((m.start(), m.end(), rule))

            for x in range(min(self._cols, len(cells))):
                px = self._margin_x + x * self._cell_w
                cell = cells[x]
                if cell is None or not cell.data:
                    continue

                fg = self._resolve_color(cell.fg, self._default_fg)
                bg = self._resolve_color(cell.bg, self._default_bg)
                if cell.reverse:
                    fg, bg = bg, fg

                if is_in_sel:
                    fg = self._sel_fg
                elif bg != self._default_bg:
                    painter.fillRect(px, py, self._cell_w, self._cell_h, bg)

                for start, end, rule in hl_spans:
                    if start <= x < end:
                        fg = rule.fg
                        if rule.bg:
                            painter.fillRect(px, py, self._cell_w, self._cell_h, rule.bg)
                        break

                is_bold = False
                for start, end, rule in hl_spans:
                    if start <= x < end and rule.bold:
                        is_bold = True
                        break

                if is_bold:
                    bold_font = QFont(self._font)
                    bold_font.setBold(True)
                    painter.setFont(bold_font)
                else:
                    painter.setFont(self._font)

                painter.setPen(QPen(fg))
                painter.drawText(px, py + self._fm.ascent(), cell.data)

                for start, end, rule in hl_spans:
                    if start <= x < end and rule.underline:
                        uy = py + self._cell_h - 2
                        painter.setPen(QPen(rule.fg, 1))
                        painter.drawLine(px, uy, px + self._cell_w - 1, uy)
                        break

        if at_bottom:
            cursor = self._screen.cursor
            if cursor and not self._selecting:
                cur_in_sel = has_sel and sy <= cursor.y <= ey if has_sel else False
                if not cur_in_sel:
                    painter.setPen(QPen(self._default_fg))
                    cx = self._margin_x + cursor.x * self._cell_w
                    cy = self._margin_y + cursor.y * self._cell_h
                    painter.fillRect(cx, cy, self._cell_w, self._cell_h, QColor(self._default_fg))
                    if cursor.x < self._cols:
                        row = self._screen.buffer.get(cursor.y, {})
                        cell = row.get(cursor.x)
                        if cell and cell.data:
                            painter.setPen(QPen(self._default_bg))
                            painter.drawText(cx, cy + self._fm.ascent(), cell.data)

        self._draw_scrollbar(painter)
        self._draw_scroll_indicator(painter)
        painter.end()

    def _scrollbar_rect(self):
        top = self._get_top_row()
        if top <= 0:
            return None
        total = top + self._vis_rows
        bar_h = max(20, int(self.height() * self._vis_rows / total))
        bar_y = int(((top - self._scroll_off) / total) * self.height())
        bar_y = max(0, min(bar_y, self.height() - bar_h))
        from PyQt6.QtCore import QRect
        return QRect(self.width() - 8, bar_y, 7, bar_h)

    def _draw_scrollbar(self, painter: QPainter):
        rect = self._scrollbar_rect()
        if rect:
            color = QColor("#88c0d0") if self._sb_dragging else QColor("#4c566a")
            painter.fillRect(rect, color)

    def _draw_scroll_indicator(self, painter: QPainter):
        if self._scroll_off == 0:
            return
        painter.setPen(QPen(QColor("#88c0d0")))
        painter.setFont(QFont("JetBrains Mono", 10))
        msg = f"↑ {self._scroll_off} lines (scroll down to return)"
        tw = painter.fontMetrics().horizontalAdvance(msg)
        painter.fillRect(self.width() // 2 - tw // 2 - 8, 2, tw + 16, 20, QColor("#3b4252"))
        painter.drawText(self.width() // 2 - tw // 2, 16, msg)

    def _resolve_color(self, name, default: QColor) -> QColor:
        if not name or name == "default":
            return default
        hex_str = self._ansi_colors.get(str(name))
        if hex_str:
            return QColor(hex_str)
        try:
            c = QColor(str(name))
            if c.isValid():
                return c
        except Exception:
            pass
        return default

    def get_all_text(self) -> str:
        lines = []
        for y in range(self._vis_rows):
            cells = self._get_display_line(y)
            if cells is None:
                continue
            line = "".join(
                cell.data if cell and cell.data else " "
                for cell in cells
            )
            lines.append(line.rstrip())
        return "\n".join(lines)

    def resizeEvent(self, event):
        avail_w = self.width() - self._margin_x - 4
        avail_h = self.height() - self._margin_y * 2
        new_cols = max(1, avail_w // self._cell_w)
        new_rows = max(1, avail_h // self._cell_h)
        if new_cols != self._cols or new_rows != self._vis_rows:
            self._cols = new_cols
            self._vis_rows = new_rows
            self._buf_rows = new_rows + 5000
            self._screen.resize(self._buf_rows, new_cols)
            if self._pty:
                self._pty.resize(new_cols, new_rows)
        super().resizeEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if self._pty is None and self._serial is None:
            return

        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_Backtab:
            self._write(b"\x1b[Z")
            return

        if (modifiers & Qt.KeyboardModifier.ControlModifier and
                modifiers & Qt.KeyboardModifier.ShiftModifier):
            if key == Qt.Key.Key_C:
                self._copy()
                return
            elif key == Qt.Key.Key_V:
                self._paste()
                return

        if key == Qt.Key.Key_PageUp:
            self._scroll_up(self._vis_rows)
            return
        elif key == Qt.Key.Key_PageDown:
            self._scroll_down(self._vis_rows)
            return

        if self._scroll_off > 0:
            self._scroll_off = 0
            self.update()

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            ctrl_map = {
                Qt.Key.Key_A: b"\x01", Qt.Key.Key_E: b"\x05",
                Qt.Key.Key_K: b"\x0b", Qt.Key.Key_U: b"\x15",
                Qt.Key.Key_W: b"\x17", Qt.Key.Key_L: b"\x0c",
                Qt.Key.Key_C: b"\x03", Qt.Key.Key_Z: b"\x1a",
                Qt.Key.Key_D: b"\x04", Qt.Key.Key_R: b"\x12",
            }
            if key in ctrl_map:
                self._sel_start = None
                self._sel_end = None
                self._write(ctrl_map[key])
                self.update()
                return

        self._sel_start = None
        self._sel_end = None
        self.update()

        text = event.text()

        key_map = {
            Qt.Key.Key_Return: b"\r", Qt.Key.Key_Enter: b"\r",
            Qt.Key.Key_Backspace: b"\x7f", Qt.Key.Key_Tab: b"\t",
            Qt.Key.Key_Escape: b"\x1b",
            Qt.Key.Key_Up: b"\x1b[A", Qt.Key.Key_Down: b"\x1b[B",
            Qt.Key.Key_Right: b"\x1b[C", Qt.Key.Key_Left: b"\x1b[D",
            Qt.Key.Key_Home: b"\x1b[H", Qt.Key.Key_End: b"\x1b[F",
            Qt.Key.Key_Delete: b"\x1b[3~", Qt.Key.Key_Insert: b"\x1b[2~",
            Qt.Key.Key_F1: b"\x1bOP", Qt.Key.Key_F2: b"\x1bOQ",
            Qt.Key.Key_F3: b"\x1bOR", Qt.Key.Key_F4: b"\x1bOS",
            Qt.Key.Key_F5: b"\x1b[15~", Qt.Key.Key_F6: b"\x1b[17~",
            Qt.Key.Key_F7: b"\x1b[18~", Qt.Key.Key_F8: b"\x1b[19~",
            Qt.Key.Key_F9: b"\x1b[20~", Qt.Key.Key_F10: b"\x1b[21~",
            Qt.Key.Key_F11: b"\x1b[23~", Qt.Key.Key_F12: b"\x1b[24~",
        }

        if key in key_map:
            self._write(key_map[key])
        elif text:
            self._write(text.encode("utf-8"))
        else:
            super().keyPressEvent(event)

    def _scroll_up(self, n: int):
        max_off = self._get_top_row()
        self._scroll_off = min(self._scroll_off + n, max_off)
        if not self._selecting:
            self._sel_start = None
            self._sel_end = None
        self.update()

    def _scroll_down(self, n: int):
        self._scroll_off = max(self._scroll_off - n, 0)
        if not self._selecting:
            self._sel_start = None
            self._sel_end = None
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if delta > 0:
            self._scroll_up(3)
        elif delta < 0:
            self._scroll_down(3)

    def _write(self, data: bytes):
        if self._pty:
            self._pty.write(data)
        elif self._serial:
            self._serial.write(data)

    def focusNextPrevChild(self, next: bool) -> bool:
        return False

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            sb = self._scrollbar_rect()
            if sb and sb.contains(event.pos()):
                self._sb_dragging = True
                self._sb_drag_start_y = event.pos().y()
                self._sb_drag_start_off = self._scroll_off
                return
            self.setFocus()
            cell = self._cell_from_pos(event.pos())
            self._sel_start = QPoint(cell.x(), cell.y())
            self._sel_end = QPoint(cell.x(), cell.y())
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._sb_dragging:
            dy = self._sb_drag_start_y - event.pos().y()
            top = self._get_top_row()
            total = top + self._vis_rows
            if total > self._vis_rows:
                max_off = top
                scroll_range = max(1, self.height() - max(20, int(self.height() * self._vis_rows / total)))
                line_per_px = max_off / scroll_range
                new_off = self._sb_drag_start_off + int(dy * line_per_px)
                self._scroll_off = max(0, min(new_off, max_off))
                self.update()
            return
        sb = self._scrollbar_rect()
        if sb and sb.contains(event.pos()):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.IBeamCursor)
        if self._selecting:
            cell = self._cell_from_pos(event.pos())
            new_end = QPoint(cell.x(), cell.y())
            if new_end != self._sel_end:
                self._sel_end = new_end
                self.update()

            y = event.pos().y()
            margin = self._cell_h * 2
            if y < margin and self._get_top_row() > self._scroll_off:
                self._auto_scroll_dir = -1
                if not self._auto_scroll_timer.isActive():
                    self._auto_scroll_timer.start(50)
            elif y > self.height() - margin and self._scroll_off > 0:
                self._auto_scroll_dir = 1
                if not self._auto_scroll_timer.isActive():
                    self._auto_scroll_timer.start(50)
            else:
                self._auto_scroll_timer.stop()
                self._auto_scroll_dir = 0

    def _auto_scroll_tick(self):
        if not self._selecting:
            self._auto_scroll_timer.stop()
            return
        if self._auto_scroll_dir == -1:
            self._scroll_up(1)
        elif self._auto_scroll_dir == 1:
            self._scroll_down(1)
        else:
            self._auto_scroll_timer.stop()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._sb_dragging:
                self._sb_dragging = False
                return
            self._selecting = False
            self._auto_scroll_timer.stop()
            self._auto_scroll_dir = 0
            has_real_sel = (
                self._sel_start is not None
                and self._sel_end is not None
                and (self._sel_start.x() != self._sel_end.x()
                     or self._sel_start.y() != self._sel_end.y())
            )
            if has_real_sel:
                self._copy()
            else:
                self._sel_start = None
                self._sel_end = None
            self.update()

    def minimumSizeHint(self):
        return self.sizeHint()

    def sizeHint(self):
        return QSize(self._cols * self._cell_w, self._vis_rows * self._cell_h)
