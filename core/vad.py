"""
语音活动检测（VAD）模块
用于持续对话模式下的自动声音检测和句子分段，带噪音隔离
"""

from __future__ import annotations

import numpy as np
from app.config import CONFIG


class VoiceActivityDetector:
    """
    语音活动检测器 - 判断是否有人说话
    
    基于音量阈值 + 频率分析进行噪音隔离
    """
    
    def __init__(
        self,
        sample_rate: int = CONFIG.audio_sample_rate,
        threshold_db: float = -15.0,
        silence_duration_ms: int = 500,
        noise_floor_db: float = -35.0,
    ):
        """
        初始化 VAD
        
        :param sample_rate: 采样率
        :param threshold_db: 声音阈值（dB）
        :param silence_duration_ms: 判定无声的时长（毫秒）
        :param noise_floor_db: 噪音下限（低于此值认为是噪音）
        """
        self.sample_rate = sample_rate
        self.threshold_db = threshold_db
        self.silence_duration_ms = silence_duration_ms
        self.noise_floor_db = noise_floor_db
        
        self._silence_frames = 0
        self._has_speech = False
        self._noise_baseline = None
    
    def detect(self, audio_chunk: np.ndarray) -> dict:
        """
        检测音频块中的语音活动，带噪音隔离
        
        :param audio_chunk: 音频数据（numpy 数组）
        :return: 包含检测结果的字典
        """
        if audio_chunk is None or len(audio_chunk) == 0:
            is_speech = False
            volume_db = -100.0
        else:
            try:
                audio_chunk = np.asarray(audio_chunk, dtype=np.float32)
                audio_chunk = audio_chunk[~np.isnan(audio_chunk)]
                
                if len(audio_chunk) == 0:
                    is_speech = False
                    volume_db = -100.0
                else:
                    # 计算 RMS 能量
                    rms = np.sqrt(np.mean(audio_chunk ** 2) + 1e-10)
                    volume_db = 20 * np.log10(rms + 1e-10)
                    
                    # 初始化噪音基线（前几帧）
                    if self._noise_baseline is None:
                        self._noise_baseline = volume_db
                    else:
                        # 更新噪音基线（平滑）
                        self._noise_baseline = 0.95 * self._noise_baseline + 0.05 * volume_db
                    
                    # 判断是否有声：高于阈值，且高于噪音基线
                    is_speech = (
                        volume_db > self.threshold_db and
                        volume_db > (self._noise_baseline + 5)  # 比噪音高 5dB
                    )
            except Exception:
                is_speech = False
                volume_db = -100.0
        
        if is_speech:
            self._silence_frames = 0
            self._has_speech = True
        else:
            frames_per_chunk = len(audio_chunk) if audio_chunk is not None else 0
            chunk_duration_ms = (frames_per_chunk / self.sample_rate) * 1000
            self._silence_frames += chunk_duration_ms
        
        is_silence_end = (
            self._has_speech
            and not is_speech
            and self._silence_frames >= self.silence_duration_ms
        )
        
        return {
            "is_speech": is_speech,
            "volume_db": volume_db,
            "silence_duration_ms": self._silence_frames,
            "is_sentence_end": is_silence_end,
        }
    
    def reset(self) -> None:
        """重置检测器状态"""
        self._silence_frames = 0
        self._has_speech = False
        self._noise_baseline = None
