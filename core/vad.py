"""
语音活动检测（VAD）模块
用于持续对话模式下的自动声音检测和句子分段
"""

from __future__ import annotations

import numpy as np
from app.config import CONFIG


class VoiceActivityDetector:
    """
    语音活动检测器 - 判断是否有人说话
    
    基于音量阈值判断，轻量级实现无需额外模型
    """
    
    def __init__(
        self,
        sample_rate: int = CONFIG.audio_sample_rate,
        threshold_db: float = -40.0,  # dB 阈值
        silence_duration_ms: int = 800,  # 无声持续时长
    ):
        """
        初始化 VAD
        
        :param sample_rate: 采样率
        :param threshold_db: 声音阈值（dB）
        :param silence_duration_ms: 判定无声的时长（毫秒）
        """
        self.sample_rate = sample_rate
        self.threshold_db = threshold_db
        self.silence_duration_ms = silence_duration_ms
        
        # 无声帧计数器
        self._silence_frames = 0
        self._has_speech = False
    
    def detect(self, audio_chunk: np.ndarray) -> dict:
        """
        检测音频块中的语音活动
        
        :param audio_chunk: 音频数据（numpy 数组）
        :return: 包含 is_speech、volume_db、silence_duration_ms 的字典
        """
        # 计算 RMS 能量
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        # 转换为 dB
        volume_db = 20 * np.log10(rms + 1e-10)
        
        # 判断是否有声
        is_speech = volume_db > self.threshold_db
        
        if is_speech:
            self._silence_frames = 0
            self._has_speech = True
        else:
            # 计算无声时长
            frames_per_chunk = len(audio_chunk)
            chunk_duration_ms = (frames_per_chunk / self.sample_rate) * 1000
            self._silence_frames += chunk_duration_ms
        
        # 判断是否达到无声时长
        is_silence_end = (
            self._has_speech
            and not is_speech
            and self._silence_frames >= self.silence_duration_ms
        )
        
        return {
            "is_speech": is_speech,
            "volume_db": volume_db,
            "silence_duration_ms": self._silence_frames,
            "is_sentence_end": is_silence_end,  # 检测到句子结束
        }
    
    def reset(self) -> None:
        """重置检测器状态"""
        self._silence_frames = 0
        self._has_speech = False
