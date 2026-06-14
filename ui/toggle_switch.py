"""
自定义 Toggle Switch 控件
实现可滑动的开关效果
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QColor, QBrush


class ToggleSwitch(QWidget):
    """自定义 Toggle Switch 开关控件"""
    
    toggled = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 28)
        
        self._is_checked = True
        self._slider_pos = 24.0  # 初始位置
        self._target_pos = 24.0
        self._animation_timer = QTimer()
        self._animation_timer.timeout.connect(self._update_animation)
        
    def sizeHint(self):
        return QSize(50, 28)
    
    def set_checked(self, checked):
        """设置开关状态"""
        if self._is_checked != checked:
            self._is_checked = checked
            self._target_pos = 24.0 if checked else 2.0
            self._animation_timer.start(16)  # 60fps
            self.toggled.emit(checked)
    
    def is_checked(self):
        return self._is_checked
    
    def _update_animation(self):
        """更新动画"""
        # 平滑移动
        diff = self._target_pos - self._slider_pos
        if abs(diff) < 0.5:
            self._slider_pos = self._target_pos
            self._animation_timer.stop()
        else:
            self._slider_pos += diff * 0.2
        
        self.update()
    
    def mousePressEvent(self, event):
        """点击切换"""
        self.set_checked(not self._is_checked)
    
    def paintEvent(self, event):
        """绘制开关"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 背景槽颜色
        bg_color = QColor(16, 185, 129) if self._is_checked else QColor(209, 213, 219)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(2, 2, 46, 24, 12, 12)
        
        # 白色圆点
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(int(self._slider_pos), 4, 20, 20)
