from __future__ import annotations

import cv2
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from core.audio import AudioRecorder
from core.camera import CameraService


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI 视觉对话助手")
        self.resize(1200, 800)

        self.camera = CameraService()
        self.audio = AudioRecorder()

        self.video_label = QLabel("摄像头未启动")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumHeight(480)
        self.video_label.setStyleSheet("background: #111827; color: white; border-radius: 8px;")

        self.status_label = QLabel("状态：准备就绪")
        self.status_label.setStyleSheet("color: #374151; padding: 8px 0;")

        self.record_label = QLabel("录音状态：未开始")
        self.record_label.setStyleSheet("color: #374151; padding: 8px 0;")

        self.start_audio_button = QPushButton("开始录音")
        self.start_audio_button.clicked.connect(self.start_recording)

        self.stop_audio_button = QPushButton("停止录音")
        self.stop_audio_button.clicked.connect(self.stop_recording)
        self.stop_audio_button.setEnabled(False)

        button_row = QHBoxLayout()
        button_row.addWidget(self.start_audio_button)
        button_row.addWidget(self.stop_audio_button)
        button_row.addStretch()

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(self.video_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.record_label)
        layout.addLayout(button_row)
        self.setCentralWidget(central)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        if self.camera.open():
            self.status_label.setText("状态：摄像头已启动")
        else:
            self.status_label.setText("状态：摄像头启动失败，请检查设备权限")

    def start_recording(self) -> None:
        if self.audio.start():
            self.record_label.setText("录音状态：录音中")
            self.start_audio_button.setEnabled(False)
            self.stop_audio_button.setEnabled(True)
        else:
            self.record_label.setText("录音状态：录音启动失败，请检查麦克风")

    def stop_recording(self) -> None:
        self.audio.stop()
        self.record_label.setText(f"录音状态：已停止，已采集 {len(self.audio.frames)} 段音频")
        self.start_audio_button.setEnabled(True)
        self.stop_audio_button.setEnabled(False)

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
        self.audio.stop()
        super().closeEvent(event)
