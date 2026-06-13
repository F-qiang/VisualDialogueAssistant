from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np

from app.prompts import SYSTEM_PROMPT
from core.audio import AudioRecorder
from core.camera import CameraService
from core.context import ContextManager
from core.router import need_vision
from core.vision import check_brightness, check_sharpness, compress_frame
from services.asr_client import ASRClient
from services.llm_client import LLMClient
from services.tts_client import TTSClient
from services.vlm_client import VLMClient
from utils.error_handler import get_fallback_response


class AppPipeline:
    """
    应用主流程管理器。

    统一编排摄像头采集、音频录制、语音识别、意图路由、
    LLM/VLM 推理、TTS 合成等各个模块的生命周期和执行流程。

    主窗口不再直接操作各个客户端，而是通过 pipeline 的高级接口
    触发功能，pipeline 负责各个模块之间的协调和状态管理。
    """

    def __init__(self) -> None:
        self.camera = CameraService()
        self.audio = AudioRecorder()
        self.ctx = ContextManager()

        # 各个服务实例
        self._asr = ASRClient()
        self._llm = LLMClient()
        self._vlm = VLMClient()
        self._tts = TTSClient()

        # 当前摄像头帧（用于视觉问答时的图像）
        self._current_frame: np.ndarray | None = None
        
        # PR11：画面变化检测与视觉缓存
        self._prev_frame: np.ndarray | None = None  # 上一帧
        self._last_vision_result: str | None = None  # 缓存的 VLM 结果
        self._vision_cache_hits = 0  # 缓存命中次数

    def capture_frame(self) -> bool:
        """
        捕获一帧摄像头画面。

        :return: 是否成功捕获。
        """
        ret, frame = self.camera.read_frame()
        if ret and frame is not None:
            self._prev_frame = self._current_frame  # 保存上一帧
            self._current_frame = frame
            return True
        return False

    def start_recording(self) -> bool:
        """启动麦克风录音，返回是否成功。"""
        return self.audio.start()

    def stop_recording(self) -> Path:
        """停止录音并保存为临时 WAV 文件，返回文件路径。"""
        import tempfile
        self.audio.stop()
        tmp = Path(tempfile.mktemp(suffix=".wav"))
        self.audio.save(tmp)
        return tmp

    def process_audio(self, audio_path: Path) -> tuple[str, str, Path]:
        """
        完整的音频处理流程：ASR → 意图路由 → LLM/VLM → TTS。

        任何环节失败时自动降级到纯文本兜底回复，确保系统不完全失能。

        :param audio_path: 待处理的 WAV 文件路径。
        :return: (识别文本, AI 回复, TTS 文件路径)
        """
        try:
            # Step 1：ASR 识别
            text = self._asr.transcribe(audio_path)
            if not text:
                # ASR 失败，降级到纯文本兜底
                reply = get_fallback_response("")
                return "", reply, Path()

            # Step 2：意图路由，判断是否需要视觉
            if need_vision(text) and self._current_frame is not None:
                # 画质检测
                if not check_brightness(self._current_frame):
                    reply = "【画面光线偏暗，请改善光线后重试】"
                    return text, reply, Path()
                if not check_sharpness(self._current_frame):
                    reply = "【画面模糊，请保持摄像头稳定后重试】"
                    return text, reply, Path()

                # PR11：检测画面是否变化
                from core.vision import motion_detect
                if motion_detect(self._prev_frame, self._current_frame):
                    # 画面变化，调用新的 VLM
                    image_bytes = compress_frame(self._current_frame)
                    reply = self._vlm.chat_with_image(
                        image_bytes, text, self.ctx.get()
                    )
                    self._last_vision_result = reply  # 缓存结果
                else:
                    # 画面未变，复用缓存
                    reply = self._last_vision_result or "【画面未变，沿用上次识别结果】"
                    self._vision_cache_hits += 1
                
                if not reply:
                    # VLM 失败，降级到纯文本 LLM
                    messages = (
                        [{"role": "system", "content": SYSTEM_PROMPT}]
                        + self.ctx.get()
                        + [{"role": "user", "content": text}]
                    )
                    reply = self._llm.chat(messages)
            else:
                # 调用 LLM
                messages = (
                    [{"role": "system", "content": SYSTEM_PROMPT}]
                    + self.ctx.get()
                    + [{"role": "user", "content": text}]
                )
                reply = self._llm.chat(messages)

            # 如果所有 AI 服务都失败，使用最后的兜底回复
            if not reply:
                reply = get_fallback_response(text)

            # Step 3：更新上下文
            self.ctx.add("user", text)
            self.ctx.add("assistant", reply)

            # Step 4：TTS 合成
            tts_path = Path()
            if reply:
                tts_file = self._tts.synthesize(reply)
                if tts_file.stat().st_size > 0:
                    tts_path = tts_file

            return text, reply, tts_path

        except Exception as e:
            # 捕获所有异常，返回兜底回复
            fallback = get_fallback_response("")
            return "", fallback, Path()

    def clear_context(self) -> None:
        """清空对话历史。"""
        self.ctx.clear()

    def release_resources(self) -> None:
        """释放所有资源。"""
        self.camera.release()
        self.audio.stop()
