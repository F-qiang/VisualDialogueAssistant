from __future__ import annotations

import os
import tempfile
from pathlib import Path

import cv2
from PyQt5.QtCore import QThread, QTimer, Qt, pyqtSignal as Signal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QSplitter,
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
from ui.toggle_switch import ToggleSwitch


# 全局视觉缓存
_last_vision_result = None
_prev_frame = None


class _Worker(QThread):
    """后台工作线程，执行 ASR → 路由 → LLM/VLM → TTS。"""
    finished = Signal(str, str, str)
    _last_frame_hash = None  # 类级别变量，跨实例共享

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
            
            # 使用画面哈希检测真实变化（比 motion_detect 更准确）
            import hashlib
            frame_hash = hashlib.md5(self._frame.tobytes()).hexdigest()[:8]
            
            # 如果画面哈希相同且有缓存，复用结果
            if _Worker._last_frame_hash is not None and _Worker._last_frame_hash == frame_hash and _last_vision_result:
                reply = _last_vision_result
                stats.record_vision_cache_hit()
            else:
                # 画面变化或首次，调用 VLM
                image_bytes = compress_frame(self._frame)
                reply = VLMClient().chat_with_image(image_bytes, text, self._history)
                _last_vision_result = reply
                _Worker._last_frame_hash = frame_hash
                stats.record_vlm_call()
            
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
            cfg = stats.get_tts_config()
            tts_file = TTSClient().synthesize(
                reply,
                speed=cfg["speed"],
                volume=cfg["volume"],
            )
            if tts_file.stat().st_size > 0:
                tts_path = str(tts_file)

        self.finished.emit(text, reply, tts_path)


class MainWindow(QMainWindow):
    """主窗口 - 支持 AUTO 模式和手动模式"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI 视觉对话助手")
        self.resize(1200, 800)

        self.camera = CameraService()
        self.audio = AudioRecorder()
        self.ctx = ContextManager()
        self._worker: _Worker | None = None
        self._current_frame = None
        self._auto_mode = True  # AUTO 模式（默认启用）
        self._recording = False  # 手动模式下是否正在录音

        # 视频预览区
        self.video_label = QLabel("摄像头未启动")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumHeight(400)
        self.video_label.setStyleSheet("background: #111827; color: white; border-radius: 8px;")

        # 对话记录区
        self.chat_box = QTextEdit()
        self.chat_box.setReadOnly(True)
        self.chat_box.setMinimumHeight(180)
        self.chat_box.setStyleSheet("background: #f9fafb; border-radius: 6px; padding: 8px;")

        # 成本统计面板（保留用于显示详细信息）
        self.stats_label = QLabel("API 调用统计：\nLLM: 0 | VLM: 0\n缓存命中: 0 | 成本节省: 0.0%")
        self.stats_label.setStyleSheet("background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 8px;")

        # 一行统计标签（仅保留详细面板，避免重复展示）
        self.stats_one_line_label = QLabel()
        self.stats_one_line_label.setVisible(False)
        self.stats_one_line_label.setStyleSheet("color: #374151; font-size: 13px;")

        # PR17：TTS 控制面板
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.speed_slider.valueChanged.connect(self._on_tts_config_changed)
        self.volume_slider.valueChanged.connect(self._on_tts_config_changed)

        # PR19：设置面板
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["默认", "浅色", "深色"])
        self.theme_combo.currentTextChanged.connect(self._save_settings)

        # PR20：导出按钮
        self.export_btn = QPushButton("导出报告")
        self.export_btn.clicked.connect(self._export_report)

        # PR21：性能面板
        self.perf_label = QLabel("性能监控：\n等待数据…")
        self.perf_label.setStyleSheet("background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 8px;")
        self.perf_timer = QTimer(self)
        self.perf_timer.timeout.connect(self._update_performance)
        self.perf_timer.start(1000)

        # 按钮区状态显示
        self.btn_status_label = QLabel("")
        self.btn_status_label.setStyleSheet("color: #1f2937; font-size: 13px; font-weight: bold;")

        # 按钮区 - AUTO 切换 + 状态显示 + 录音按钮 + 清空按钮
        auto_label = QLabel("Auto")
        auto_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        
        self.auto_switch = ToggleSwitch()
        self.auto_switch.set_checked(True)
        self.auto_switch.toggled.connect(self._toggle_auto_mode)
        
        self.record_btn = QPushButton("开始录音")
        self.record_btn.setEnabled(False)  # AUTO 模式下禁用
        self.record_btn.clicked.connect(self._toggle_recording)

        self.clear_btn = QPushButton("清空对话")
        self.clear_btn.clicked.connect(self._clear_context)

        central = QWidget(self)
        main_layout = QHBoxLayout(central)
        
        # 左侧面板（摄像头 + 统计 + 状态 + 按钮）
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 摄像头区域
        left_layout.addWidget(self.video_label, 3)
        
        # 统计一行（已隐藏，保留字段但不重复展示）
        left_layout.addWidget(self.stats_one_line_label)
        
        # 状态信息一行
        left_layout.addWidget(self.btn_status_label)
        
        # 按钮行（Auto + 录音 + 清空）
        btn_layout = QHBoxLayout()
        auto_label = QLabel("Auto")
        auto_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        btn_layout.addWidget(auto_label)
        btn_layout.addWidget(self.auto_switch)
        btn_layout.addWidget(self.record_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.clear_btn)
        left_layout.addLayout(btn_layout)

        # PR17/19/20/21 控制区域
        left_layout.addWidget(QLabel("TTS 语速"))
        left_layout.addWidget(self.speed_slider)
        left_layout.addWidget(QLabel("TTS 音量"))
        left_layout.addWidget(self.volume_slider)
        left_layout.addWidget(QLabel("主题"))
        left_layout.addWidget(self.theme_combo)
        left_layout.addWidget(self.export_btn)
        left_layout.addWidget(self.perf_label)
        left_layout.addWidget(self.stats_label)
        
        # 右侧面板（对话记录）
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(self.chat_box)
        
        # 左右分割
        main_layout.addWidget(left_widget, 2)  # 40%
        main_layout.addWidget(right_widget, 3)  # 60%
        
        self.setCentralWidget(central)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(30)

        # 定时更新统计面板
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(500)
        self._update_stats()
        self._load_settings()
        self._on_tts_config_changed()

        if self.camera.open():
            self.btn_status_label.setText("摄像头已启动，AUTO 模式开启")
        else:
            self.btn_status_label.setText("摄像头启动失败")
        
        # 启动 AUTO 模式
        self._enable_auto_mode()

    def _toggle_auto_mode(self, checked: bool) -> None:
        """切换 AUTO 模式和手动模式"""
        self._auto_mode = checked
        if self._auto_mode:
            self.record_btn.setEnabled(False)
            self._enable_auto_mode()
        else:
            self.record_btn.setEnabled(True)
            self._disable_auto_mode()
    
    def _enable_auto_mode(self) -> None:
        """启用 AUTO 模式 - 自动监听发送"""
        self.audio.set_continuous_mode(True, self._on_sentence_end)
        self.btn_status_label.setText("AUTO 模式，自动监听中…")
    
    def _disable_auto_mode(self) -> None:
        """禁用 AUTO 模式 - 启用手动控制"""
        self.audio.set_continuous_mode(False)
        self.record_btn.setText("开始录音")
        self.btn_status_label.setText("手动模式，点击开始录音")
    
    def _on_sentence_end(self) -> None:
        """AUTO 模式：检测到句子结束，自动发送"""
        if self.audio.is_recording and len(self.audio.frames) > 0:
            print("[DEBUG] 检测到句子结束，准备发送")
            self._stop_and_send_auto()
    
    def _toggle_recording(self) -> None:
        """手动模式：切换录音"""
        if self._recording:
            self._stop_and_send()
        else:
            self._start_recording()
    
    def _start_recording(self) -> None:
        """手动模式：开始录音"""
        if self.audio.start():
            self._recording = True
            self.record_btn.setText("停止并发送")
        else:
            pass
    
    def _stop_and_send(self) -> None:
        """手动模式：停止录音并发送"""
        self._recording = False
        self.audio.stop()
        self.record_btn.setEnabled(False)

        tmp = Path(tempfile.mktemp(suffix=".wav"))
        self.audio.save(tmp)

        self._worker = _Worker(tmp, self.ctx.get(), self._current_frame)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _stop_and_send_auto(self) -> None:
        """AUTO 模式：停止录音并发送，然后继续监听"""
        self.btn_status_label.setText("处理中…")

        tmp = Path(tempfile.mktemp(suffix=".wav"))
        self.audio.save(tmp)

        self._worker = _Worker(tmp, self.ctx.get(), self._current_frame)
        self._worker.finished.connect(self._on_done_auto)
        self._worker.start()

    def _on_done(self, user_text: str, reply: str, tts_path: str) -> None:
        """手动模式：完成回调"""
        if not user_text:
            self.record_btn.setEnabled(True)
            self.record_btn.setText("开始录音")
            self.audio.clear()
            return

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

        self.record_btn.setEnabled(True)
        self.record_btn.setText("开始录音")
        self.audio.clear()

    def _on_done_auto(self, user_text: str, reply: str, tts_path: str) -> None:
        """AUTO 模式：完成回调，继续监听"""
        try:
            if user_text:
                self.ctx.add("user", user_text)
                self.ctx.add("assistant", reply)
                self.chat_box.append(f"<b>你：</b>{user_text}")
                self.chat_box.append(f"<b>AI：</b>{reply or '（无回复）'}")
                self.chat_box.append("")

                if tts_path:
                    # 暂停监听
                    self.audio.stop()
                    try:
                        # 后台启动播放
                        import subprocess
                        subprocess.Popen(['start', tts_path], shell=True, 
                                       stdout=subprocess.DEVNULL, 
                                       stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
                    
                    # 立即恢复监听
                    self.audio.clear()
                    self.audio.vad.reset()
                    self.audio.start()
                    return
            
            # 没有 TTS 时立即恢复监听
            self.audio.clear()
            self.audio.vad.reset()
            self.audio.start()
        except Exception as e:
            # 异常时也要恢复监听
            try:
                self.audio.clear()
                self.audio.vad.reset()
                self.audio.start()
            except:
                pass

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

    def _on_tts_config_changed(self) -> None:
        """更新 TTS 配置。"""
        stats.set_tts_config(self.speed_slider.value() / 100, self.volume_slider.value())
        self._save_settings()

    def _save_settings(self) -> None:
        """保存用户设置。"""
        try:
            settings_path = Path(tempfile.gettempdir()) / "visual_dialogue_settings.json"
            settings_path.write_text(
                __import__("json").dumps(
                    {
                        "tts_speed": self.speed_slider.value(),
                        "tts_volume": self.volume_slider.value(),
                        "theme": self.theme_combo.currentText(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load_settings(self) -> None:
        """加载用户设置。"""
        try:
            settings_path = Path(tempfile.gettempdir()) / "visual_dialogue_settings.json"
            if not settings_path.exists():
                return
            data = __import__("json").loads(settings_path.read_text(encoding="utf-8"))
            self.speed_slider.setValue(int(data.get("tts_speed", 100)))
            self.volume_slider.setValue(int(data.get("tts_volume", 100)))
            theme = data.get("theme")
            if theme:
                index = self.theme_combo.findText(theme)
                if index >= 0:
                    self.theme_combo.setCurrentIndex(index)
        except Exception:
            pass

    def _export_report(self) -> None:
        """导出使用报告。"""
        timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = Path(tempfile.gettempdir())
        stats.export_to_json(export_dir / f"report_{timestamp}.json")
        stats.export_to_csv(export_dir / f"report_{timestamp}.csv")
        self.btn_status_label.setText(f"报告已导出至 {export_dir}")

    def _update_performance(self) -> None:
        """刷新性能面板。"""
        metrics = stats.get_performance_metrics()
        if not metrics:
            self.perf_label.setText("性能监控：\n等待数据…")
            return
        self.perf_label.setText(
            "性能监控：\n"
            f"平均响应: {metrics.get('avg_latency', 0):.2f}s\n"
            f"最大响应: {metrics.get('max_latency', 0):.2f}s\n"
            f"内存占用: {metrics.get('memory_usage', 0):.1f} MB\n"
            f"CPU 使用: {metrics.get('cpu_percent', 0):.1f}%"
        )

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
        """更新统计面板和按钮区状态"""
        try:
            summary = stats.get_summary()
            # 一行统计标签已隐藏，不再重复展示
            one_line = f"LLM {summary['llm_calls']} | VLM {summary['vlm_calls']} | 缓存 {summary['vision_cache_hits']} | 成本 {summary['cost_saved_percent']}"
            self.stats_one_line_label.setText(one_line)
            
            # 保留原有的详细统计面板用于其他用途
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
