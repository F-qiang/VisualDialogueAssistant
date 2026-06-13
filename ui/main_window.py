from __future__ import annotations

import os
import tempfile
from pathlib import Path

import cv2
from PyQt5.QtCore import QThread, QTimer, Qt, pyqtSignal as Signal
from PyQt5.QtGui import QImage, QPixmap
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
from core.audio import AudioRecorder
from core.camera import CameraService
from core.context import ContextManager
from core.router import need_vision
from core.vision import check_brightness, check_sharpness, compress_frame, motion_detect
from services.asr_client import ASRClient
from services.llm_client import LLMClient
from services.tts_client import TTSClient
from services.vlm_client import VLMClient
from utils.logger import stats


# PR12：全局视觉缓存和上一帧保存
_last_vision_result = None
_prev_frame = None


class _Worker(QThread):
    """后台工作线程，执行 ASR → 路由 → LLM/VLM → TTS。"""
    finished = Signal(str, str, str)

    def __init__(self, audio_path: Path, history: list, frame) -> None:
        super().__init__()
        self._path = audio_path
        self._history = history
        self._frame = frame

    def run(self) -> None:
        """线程执行体。"""
        global _last_vision_result, _prev_frame
        
        text = ASRClient().transcribe(self._path)
        if not text:
            self.finished.emit("", "", "")
            return

        if need_vision(text) and self._frame is not None:
            if not check_brightness(self._frame):
                self.finished.emit(text, "【画面光线偏暗，请改善光线后重试】", "")
                return
            if not check_sharpness(self._frame):
                self.finished.emit(text, "【画面模糊，请保持摄像头稳定后重试】", "")
                return
            
            # PR12：判断画面是否变化
            if motion_detect(_prev_frame, self._frame):
                # 画面变化，调用新的 VLM
                image_bytes = compress_frame(self._frame)
                reply = VLMClient().chat_with_image(image_bytes, text, self._history)
                _last_vision_result = reply
                stats.record_vlm_call()
            else:
                # 画面未变，复用缓存
                if _last_vision_result is not None:
                    reply = _last_vision_result
                    stats.record_vision_cache_hit()
                else:
                    # 首次提问且缓存为空，调用 VLM
                    image_bytes = compress_frame(self._frame)
                    reply = VLMClient().chat_with_image(image_bytes, text, self._history)
                    _last_vision_result = reply
                    stats.record_vlm_call()
            
            # 更新上一帧
            _prev_frame = self._frame
        else:
            messages = (
                [{"role": "system", "content": SYSTEM_PROMPT}]
                + self._history
                + [{"role": "user", "content": text}]
            )
            reply = LLMClient().chat(messages)
            stats.record_llm_call()

        tts_path = ""
        if reply:
            tts_file = TTSClient().synthesize(reply)
            if tts_file.stat().st_size > 0:
                tts_path = str(tts_file)

        self.finished.emit(text, reply, tts_path)


class MainWindow(QMainWindow):
    """主窗口 - 无按钮持续对话模式"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI 视觉对话助手")
        self.resize(1200, 800)

        self.camera = CameraService()
        self.audio = AudioRecorder()
        self.ctx = ContextManager()
        self._worker: _Worker | None = None
        self._current_frame = None

        # 视频预览区
        self.video_label = QLabel("摄像头未启动")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumHeight(400)
        self.video_label.setStyleSheet("background: #111827; color: white; border-radius: 8px;")

        # 状态栏
        self.status_label = QLabel("状态：准备就绪")
        self.status_label.setStyleSheet("color: #374151; padding: 4px 0;")

        # 对话记录区
        self.chat_box = QTextEdit()
        self.chat_box.setReadOnly(True)
        self.chat_box.setMinimumHeight(180)
        self.chat_box.setStyleSheet("background: #f9fafb; border-radius: 6px; padding: 8px;")

        # 成本统计面板
        self.stats_label = QLabel("API 调用统计：\nLLM: 0 | VLM: 0\n缓存命中: 0 | 成本节省: 0.0%")
        self.stats_label.setStyleSheet("background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 8px;")

        # 按钮区 - 仅显示状态和清空
        self.status_btn = QLabel("监听中…")
        self.status_btn.setStyleSheet("padding: 8px; color: #10b981; font-weight: bold;")

        self.clear_btn = QPushButton("清空对话")
        self.clear_btn.clicked.connect(self._clear_context)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.status_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.clear_btn)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(self.video_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.chat_box)
        layout.addWidget(self.stats_label)
        layout.addLayout(btn_row)
        self.setCentralWidget(central)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(30)

        # 定时更新统计面板
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(500)
        self._update_stats()

        if self.camera.open():
            self.status_label.setText("状态：摄像头已启动，开始监听…")
        else:
            self.status_label.setText("状态：摄像头启动失败")
        
        # 启动持续对话模式 - 无需按钮
        self.audio.set_continuous_mode(True, self._on_sentence_end)

    def _on_sentence_end(self) -> None:
        """检测到句子结束，自动发送"""
        if self.audio.is_recording and len(self.audio.frames) > 0:
            self.status_label.setText("状态：处理中…")

            tmp = Path(tempfile.mktemp(suffix=".wav"))
            self.audio.save(tmp)

            self._worker = _Worker(tmp, self.ctx.get(), self._current_frame)
            self._worker.finished.connect(self._on_done_continuous)
            self._worker.start()

    def _on_done_continuous(self, user_text: str, reply: str, tts_path: str) -> None:
        """处理完成，继续监听"""
        if user_text:
            self.ctx.add("user", user_text)
            self.ctx.add("assistant", reply)
            self.chat_box.append(f"<b>你：</b>{user_text}")
            self.chat_box.append(f"<b>AI：</b>{reply or '（无回复）'}")
            self.chat_box.append("")

            if tts_path:
                try:
                    os.startfile(tts_path)
                except Exception:
                    pass
        
        # 清空缓冲，继续监听
        self.audio.clear()
        self.audio.vad.reset()
        self.status_label.setText("状态：继续监听…")

    def _clear_context(self) -> None:
        """清空对话"""
        global _last_vision_result, _prev_frame
        self.ctx.clear()
        self.chat_box.clear()
        _last_vision_result = None
        _prev_frame = None
        stats.clear()
        self.audio.clear()
        self.audio.vad.reset()
        self.status_label.setText("状态：对话已清空，继续监听…")

    def _update_frame(self) -> None:
        """更新摄像头画面"""
        ret, frame = self.camera.read_frame()
        if not ret or frame is None:
            return
        
        self._current_frame = frame
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

    def _update_stats(self) -> None:
        """更新统计面板"""
        try:
            summary = stats.get_summary()
            text = (
                f"API 调用统计：\n"
                f"LLM: {summary['llm_calls']} | VLM: {summary['vlm_calls']}\n"
                f"缓存命中: {summary['vision_cache_hits']} | 成本节省: {summary['cost_saved_percent']}"
            )
            self.stats_label.setText(text)
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        """关闭事件"""
        self.camera.release()
        self.audio.stop()
        super().closeEvent(event)
