import cv2
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QMainWindow, QWidget, QVBoxLayout

from core.camera import CameraService


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI 视觉对话助手")
        self.resize(1200, 800)

        self.camera = CameraService()
        self.video_label = QLabel("摄像头未启动")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumHeight(480)
        self.video_label.setStyleSheet("background: #111827; color: white; border-radius: 8px;")

        self.status_label = QLabel("状态：准备就绪")
        self.status_label.setStyleSheet("color: #374151; padding: 8px 0;")

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(self.video_label)
        layout.addWidget(self.status_label)
        self.setCentralWidget(central)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        if self.camera.open():
            self.status_label.setText("状态：摄像头已启动")
        else:
            self.status_label.setText("状态：摄像头启动失败，请检查设备权限")

    def update_frame(self) -> None:
        ret, frame = self.camera.read_frame()
        if not ret or frame is None:
            return

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb_frame.shape
        bytes_per_line = channels * width
        image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(
            pixmap.scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def closeEvent(self, event) -> None:
        self.camera.release()
        super().closeEvent(event)
