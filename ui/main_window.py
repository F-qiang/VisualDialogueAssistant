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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.prompts import SYSTEM_PROMPT
from core.audio import AudioRecorder
from core.camera import CameraService
from core.context import ContextManager
from services.asr_client import ASRClient
from services.llm_client import LLMClient


class _Worker(QThread):
    """后台线程：ASR → LLM。"""
    finished = Signal(str, str)  # (识别文本, LLM回复)

    def __init__(self, audio_path: Path, history: list) -> None:
        super().__init__()
        self._path = audio_path
        self._history = history

    def run(self) -> None:
        text = ASRClient().transcribe(self._path)
        if not text:
            self.finished.emit("", "")
            return
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self._history + [
            {"role": "user", "content": text}
        ]
        reply = LLMClient().chat(messages)
        self.finished.emit(text, reply)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI 视觉对话助手")
        self.resize(1200, 800)

        self.camera = CameraService()
        self.audio = AudioRecorder()
        self.ctx = ContextManager()
        self._worker: _Worker | None = None

        # 视频区
        self.video_label = QLabel("摄像头未启动")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumHeight(400)
        self.video_label.setStyleSheet("background: #111827; color: white; border-radius: 8px;")

        # 状态栏
        self.status_label = QLabel("状态：准备就绪")
        self.status_label.setStyleSheet("color: #374151; padding: 4px 0;")

        # 对话区
        self.chat_box = QTextEdit()
        self.chat_box.setReadOnly(True)
        self.chat_box.setMinimumHeight(180)
        self.chat_box.setStyleSheet("background: #f9fafb; border-radius: 6px; padding: 8px;")

        # 按钮
        self.start_btn = QPushButton("开始录音")
        self.start_btn.clicked.connect(self._start_recording)
        self.stop_btn = QPushButton("停止并发送")
        self.stop_btn.clicked.connect(self._stop_and_send)
        self.stop_btn.setEnabled(False)
        self.clear_btn = QPushButton("清空对话")
        self.clear_btn.clicked.connect(self._clear_context)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(self.video_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.chat_box)
        layout.addLayout(btn_row)
        self.setCentralWidget(central)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(30)

        if self.camera.open():
            self.status_label.setText("状态：摄像头已启动")
        else:
            self.status_label.setText("状态：摄像头启动失败，请检查设备权限")

    # ---------- 录音与对话 ----------

    def _start_recording(self) -> None:
        if self.audio.start():
            self.status_label.setText("状态：录音中…")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.status_label.setText("状态：录音启动失败，请检查麦克风")

    def _stop_and_send(self) -> None:
        self.audio.stop()
        self.stop_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.status_label.setText("状态：识别中…")

        tmp = Path(tempfile.mktemp(suffix=".wav"))
        self.audio.save(tmp)

        self._worker = _Worker(tmp, self.ctx.get())
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _on_done(self, user_text: str, reply: str) -> None:
        if not user_text:
            self.status_label.setText("状态：识别失败，请检查 ASR 配置或重试")
            self.start_btn.setEnabled(True)
            self.audio.clear()
            return

        self.ctx.add("user", user_text)
        self.ctx.add("assistant", reply)
        self.chat_box.append(f"<b>你：</b>{user_text}")
        self.chat_box.append(f"<b>AI：</b>{reply or '（回复为空，请检查 LLM 配置）'}")
        self.chat_box.append("")
        self.status_label.setText("状态：回复完成")
        self.start_btn.setEnabled(True)
        self.audio.clear()

    def _clear_context(self) -> None:
        self.ctx.clear()
        self.chat_box.clear()
        self.status_label.setText("状态：对话已清空")

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
