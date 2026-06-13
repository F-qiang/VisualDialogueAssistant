from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
from PyQt5.QtCore import QThread, QTimer, Qt, pyqtSignal as Signal, QUrl
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.prompts import SYSTEM_PROMPT
from app.state import AppState
from core.audio import AudioRecorder
from core.camera import CameraService
from core.context import ContextManager
from core.router import need_vision
from core.vision import check_brightness, check_sharpness, compress_frame
from services.asr_client import ASRClient
from services.llm_client import LLMClient
from services.tts_client import TTSClient
from services.vlm_client import VLMClient


class _Worker(QThread):
    """
    后台工作线程，依次执行 ASR 识别和路由后的 LLM 或 VLM 推理，
    完成后再调用 TTS 合成语音，避免主线程阻塞。
    """

    # 信号携带三个值：(用户识别文本, AI 回复文本, 语音文件路径)
    finished = Signal(str, str, str)

    def __init__(self, audio_path: Path, history: list, frame) -> None:
        super().__init__()
        self._path = audio_path
        self._history = history
        self._frame = frame

    def run(self) -> None:
        """线程执行体：ASR → 意图路由 → LLM/VLM → TTS。"""
        # Step 1：语音识别
        text = ASRClient().transcribe(self._path)
        if not text:
            self.finished.emit("", "", "")
            return

        # Step 2：意图路由
        if need_vision(text) and self._frame is not None:
            if not check_brightness(self._frame):
                self.finished.emit(text, "【画面光线偏暗，请改善光线后重试】", "")
                return
            if not check_sharpness(self._frame):
                self.finished.emit(text, "【画面模糊，请保持摄像头稳定后重试】", "")
                return
            image_bytes = compress_frame(self._frame)
            reply = VLMClient().chat_with_image(image_bytes, text, self._history)
        else:
            messages = (
                [{"role": "system", "content": SYSTEM_PROMPT}]
                + self._history
                + [{"role": "user", "content": text}]
            )
            reply = LLMClient().chat(messages)

        # Step 3：TTS 合成，reply 为空时跳过
        tts_path = ""
        if reply:
            tts_file = TTSClient().synthesize(reply)
            if tts_file.stat().st_size > 0:
                tts_path = str(tts_file)

        self.finished.emit(text, reply, tts_path)


class MainWindow(QMainWindow):
    """
    主窗口，包含摄像头预览、对话展示和录音控制。

    布局结构：
    - 视频预览区（上）
    - 状态栏（中）
    - 对话记录区（中下）
    - 按钮区（下）
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI 视觉对话助手")
        self.resize(1200, 800)

        # 核心服务实例
        self.camera = CameraService()
        self.audio = AudioRecorder()
        self.ctx = ContextManager()
        self._worker: _Worker | None = None
        self._state = AppState.IDLE  # 当前系统状态，驱动按钮和提示

        # Qt 媒体播放器，用于播放 TTS 合成的语音
        self._audio_output = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)
        # 播放结束后自动切回 IDLE 状态
        self._player.playbackStateChanged.connect(self._on_playback_changed)

        # --- 视频预览区 ---
        self.video_label = QLabel("摄像头未启动")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumHeight(400)
        self.video_label.setStyleSheet(
            "background: #111827; color: white; border-radius: 8px;"
        )

        # --- 状态栏 ---
        self.status_label = QLabel("状态：准备就绪")
        self.status_label.setStyleSheet("color: #374151; padding: 4px 0;")

        # --- 对话记录区（只读富文本） ---
        self.chat_box = QTextEdit()
        self.chat_box.setReadOnly(True)
        self.chat_box.setMinimumHeight(180)
        self.chat_box.setStyleSheet(
            "background: #f9fafb; border-radius: 6px; padding: 8px;"
        )

        # --- 按钮区 ---
        self.start_btn = QPushButton("开始录音")
        self.start_btn.clicked.connect(self._start_recording)

        self.stop_btn = QPushButton("停止并发送")
        self.stop_btn.clicked.connect(self._stop_and_send)
        self.stop_btn.setEnabled(False)  # 未录音时禁用

        self.clear_btn = QPushButton("清空对话")
        self.clear_btn.clicked.connect(self._clear_context)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()

        # --- 整体布局 ---
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(self.video_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.chat_box)
        layout.addLayout(btn_row)
        self.setCentralWidget(central)

        # --- 摄像头刷新定时器，约 33fps ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(30)

        # 尝试打开摄像头并更新状态提示
        if self.camera.open():
            self.status_label.setText("状态：摄像头已启动")
        else:
            self.status_label.setText("状态：摄像头启动失败，请检查设备权限")

    def _set_state(self, state: AppState) -> None:
        """
        切换系统状态，并同步更新按钮的启用状态和状态栏文字。

        统一在此处控制所有状态变化，避免分散在各方法中手动操作按钮。
        """
        self._state = state
        is_idle = state == AppState.IDLE
        self.start_btn.setEnabled(is_idle)
        self.stop_btn.setEnabled(state == AppState.RECORDING)
        self.clear_btn.setEnabled(is_idle)

        labels = {
            AppState.IDLE: "状态：准备就绪",
            AppState.RECORDING: "状态：录音中…",
            AppState.THINKING: "状态：识别中…",
            AppState.SPEAKING: "状态：播报中…",
        }
        self.status_label.setText(labels[state])

    def _on_playback_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        """媒体播放结束后切回 IDLE 状态。"""
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self._set_state(AppState.IDLE)

    # ---------- 录音与对话逻辑 ----------

    def _start_recording(self) -> None:
        """开始录音，更新按钮状态和状态栏提示。"""
        if self.audio.start():
            self._set_state(AppState.RECORDING)
        else:
            self.status_label.setText("状态：录音启动失败，请检查麦克风")

    def _stop_and_send(self) -> None:
        """停止录音，保存音频文件，启动后台 ASR + 路由 + LLM/VLM 线程。"""
        self.audio.stop()
        self._set_state(AppState.THINKING)

        tmp = Path(tempfile.mktemp(suffix=".wav"))
        self.audio.save(tmp)
        _, current_frame = self.camera.read_frame()

        self._worker = _Worker(tmp, self.ctx.get(), current_frame)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _on_done(self, user_text: str, reply: str, tts_path: str) -> None:
        """
        后台线程完成回调，展示对话内容并触发语音播报。

        识别失败（user_text 为空）时给出提示并恢复按钮。
        """
        if not user_text:
            self.status_label.setText("状态：识别失败，请检查 ASR 配置或重试")
            self._set_state(AppState.IDLE)
            self.audio.clear()
            return

        self.ctx.add("user", user_text)
        self.ctx.add("assistant", reply)

        self.chat_box.append(f"<b>你：</b>{user_text}")
        self.chat_box.append(
            f"<b>AI：</b>{reply or '（回复为空，请检查 LLM 配置）'}"
        )
        self.chat_box.append("")

        if tts_path:
            self._set_state(AppState.SPEAKING)
            self._player.setSource(QUrl.fromLocalFile(tts_path))
            self._player.play()
        else:
            self._set_state(AppState.IDLE)

        self.audio.clear()

    def _clear_context(self) -> None:
        """清空对话历史和界面记录，重置到初始状态。"""
        self.ctx.clear()
        self.chat_box.clear()
        self.status_label.setText("状态：对话已清空")

    # ---------- 摄像头画面刷新 ----------

    def _update_frame(self) -> None:
        """
        定时器回调，读取最新摄像头帧并渲染到视频标签。

        读取失败时静默跳过，不影响界面其他功能。
        """
        ret, frame = self.camera.read_frame()
        if not ret or frame is None:
            return

        # BGR → RGB，再转为 Qt 图像格式
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
        """窗口关闭时释放摄像头和麦克风资源。"""
        self.camera.release()
        self.audio.stop()
        super().closeEvent(event)
