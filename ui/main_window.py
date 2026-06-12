from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QMainWindow, QWidget, QVBoxLayout

from core.camera import CameraService


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI 视觉对话助手")
        self.resize(1200, 800)

        self.camera = CameraService()
        self.video_label = QLabel("摄像头未启动")
        self.video_label.setMinimumHeight(480)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(self.video_label)
        self.setCentralWidget(central)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        self.camera.open()

    def update_frame(self) -> None:
        ret, frame = self.camera.read_frame()
        if not ret or frame is None:
            return

    def closeEvent(self, event) -> None:
        self.camera.release()
        super().closeEvent(event)
