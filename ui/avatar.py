from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QPoint, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QCursor, QPainter, QPixmap
from PyQt5.QtWidgets import QLabel


class Avatar(QLabel):
    """Avatar 动画角色（精简版）。"""

    visibility_toggled = pyqtSignal(bool)

    STATES = {
        "idle": 4,
        "listening": 4,
        "thinking": 4,
        "speaking": 4,
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.current_state = "idle"
        self.frame_index = 0
        self.frames: dict[str, list[QPixmap]] = {}
        self._fallback_size = 180
        self._asset_dir = Path(__file__).resolve().parent.parent / "assets" / "avatar"
        self._dragging = False
        self._drag_offset = QPoint(0, 0)
        self._visible_state = True
        self._load_frames()

        self.setMinimumSize(self._fallback_size, self._fallback_size)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background: rgba(17, 24, 39, 230); border-radius: 12px;")
        self.setCursor(QCursor(Qt.OpenHandCursor))
        self._normal_opacity = 1.0
        self._drag_opacity = 0.72
        self.setWindowOpacity(self._normal_opacity)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_frame)
        self.timer.start(140)
        self._show_current_frame()

    def _load_frames(self) -> None:
        """加载 4 个状态的帧，若素材缺失则回退到占位图。"""
        for state, count in self.STATES.items():
            self.frames[state] = []
            for idx in range(1, count + 1):
                path = self._asset_dir / f"{state}_{idx}.png"
                pixmap = QPixmap(str(path))
                if pixmap.isNull():
                    pixmap = self._create_placeholder_pixmap(state, idx)
                self.frames[state].append(pixmap)

    def _create_placeholder_pixmap(self, state: str, idx: int) -> QPixmap:
        """创建简易占位图，避免素材缺失导致界面空白。"""
        pixmap = QPixmap(self._fallback_size, self._fallback_size)
        colors = {
            "idle": QColor("#60a5fa"),
            "listening": QColor("#34d399"),
            "thinking": QColor("#fbbf24"),
            "speaking": QColor("#f472b6"),
        }
        pixmap.fill(colors.get(state, QColor("#9ca3af")))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.white)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, f"{state}\n{idx}")
        painter.end()
        return pixmap

    def _show_current_frame(self) -> None:
        frames = self.frames.get(self.current_state) or []
        if not frames:
            return
        self.setPixmap(
            frames[self.frame_index].scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def _next_frame(self) -> None:
        frames = self.frames.get(self.current_state) or []
        if not frames:
            return
        self.frame_index = (self.frame_index + 1) % len(frames)
        self._show_current_frame()

    def set_state(self, state: str) -> None:
        """切换状态。"""
        if state not in self.STATES:
            state = "idle"
        if state == self.current_state:
            return
        self.current_state = state
        self.frame_index = 0
        self._show_current_frame()

    def disable(self) -> None:
        """禁用 Avatar（出问题时关闭）。"""
        self._visible_state = False
        self.timer.stop()
        self.hide()
        self.visibility_toggled.emit(False)

    def toggle_visible(self) -> None:
        """切换显示状态。"""
        if self.isVisible():
            self.disable()
        else:
            self.enable()
            self.visibility_toggled.emit(True)

    def enable(self) -> None:
        """启用 Avatar。"""
        self._visible_state = True
        self.show()
        if not self.timer.isActive():
            self.timer.start(140)
        self._show_current_frame()

    def mousePressEvent(self, event) -> None:
        """按下鼠标开始拖动。"""
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_offset = event.pos()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            self.setWindowOpacity(self._drag_opacity)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """拖动 Avatar。"""
        if self._dragging and event.buttons() & Qt.LeftButton and self.parent() is not None:
            parent = self.parentWidget()
            if parent is not None:
                new_pos = self.mapToParent(event.pos() - self._drag_offset)
                max_x = max(0, parent.width() - self.width())
                max_y = max(0, parent.height() - self.height())
                new_x = max(0, min(new_pos.x(), max_x))
                new_y = max(0, min(new_pos.y(), max_y))
                self.move(new_x, new_y)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """释放鼠标结束拖动。"""
        self._dragging = False
        self.setCursor(QCursor(Qt.OpenHandCursor))
        self.setWindowOpacity(self._normal_opacity)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """双击切换显示 / 隐藏。"""
        if event.button() == Qt.LeftButton:
            self.toggle_visible()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
