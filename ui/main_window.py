from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.audio import AudioRecorder
from core.camera import CameraService
from services.asr_client import ASRClient


class _ASRWorker(QThread):
    """在独立线程里调用 ASR，避免界面卡顿。"""
    finished = Signal(str)

    def __init__(self, audio_path: Path) -> None:
        super().__init__()
        self._path = audio_path

    def run(self) -> None:
        text = ASRClient().transcribe(self._path)
        self.finished.emit(text)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI 视觉对话助手")
        self.resize(1200, 800)

        self.camera = CameraService()
        self.audio = AudioRecorder()
        self._asr_worker: _ASRWorker | None = None

        self.video_label = QLabel("摄像头未启动")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumHeight(480)
        self.video_label.setStyleSheet("background: #111827; color: white; border-radius: 8px;")

        self.status_label = QLabel("状态：准备就绪")
        self.status_label.setStyleSheet("color: #374151; padding: 8px 0;")

        self.asr_label = QLabel("识别结果：-")
        self.asr_label.setWordWrap(True)
        self.asr_label.setStyleSheet("color: #111827; padding: 8px 0;")

        self.start_btn = QPushButton("开始录音")
        self.start_btn.clicked.connect(self._start_recording)

        self.stop_btn = QPushButton("停止并识别")
        self.stop_btn.clicked.connect(self._stop_and_transcribe)
        self.stop_btn.setEnabled(False)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addStretch()

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(self.video_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.asr_label)
        layout.addLayout(btn_row)
        self.setCentralWidget(central)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(30)

        if self.camera.open():
            self.status_label.setText("状态：摄像头已启动")
        else:
            self.status_label.setText("状态：摄像头启动失败，请检查设备权限")

    # ---------- 录音与 ASR ----------

    def _start_recording(self) -> None:
        if self.audio.start():
            self.status_label.setText("状态：录音中…")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.status_label.setText("状态：录音启动失败，请检查麦克风")

    def _stop_and_transcribe(self) -> None:
        self.audio.stop()
        self.stop_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.status_label.setText("状态：识别中…")

        tmp = Path(tempfile.mktemp(suffix=".wav"))
        saved = self.audio.save(tmp)

        self._asr_worker = _ASRWorker(saved)
        self._asr_worker.finished.connect(self._on_asr_done)
        self._asr_worker.start()

    def _on_asr_done(self, text: str) -> None:
        if text:
            self.asr_label.setText(f"识别结果：{text}")
            self.status_label.setText("状态：识别完成")
        else:
            self.asr_label.setText("识别结果：识别失败，请检查 API 配置或重试")
            self.status_label.setText("状态：识别失败")
        self.start_btn.setEnabled(True)
        self.audio.clear()

    # ---------- 摄像头刷新 ----------

    def _update_frame(self) -> None:
        ret, frame = self.camera.read_frame()
        if not ret or frame is None:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(
            QPixmap.fromImage(image).scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def closeEvent(self, event) -> None:
        self.camera.release()
        self.audio.stop()
        super().closeEvent(event)
