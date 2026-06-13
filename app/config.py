import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """
    全局应用配置。

    所有字段优先从环境变量读取，缺省时使用默认值。
    通过 CONFIG 单例使用，不要在运行时修改。
    """

    app_name: str = "AI视觉对话助手"
    # 摄像头设备索引，0 表示第一个摄像头
    camera_index: int = 0
    # 音频采样率，ASR 服务通常要求 16000 Hz
    audio_sample_rate: int = 16000
    # 音频声道数，1 为单声道
    audio_channels: int = 1
    # 每次音频回调的时长（毫秒），影响录音实时性
    audio_block_duration_ms: int = 30
    # 保留的最大对话轮数，超出后自动裁剪历史
    max_context_rounds: int = 5


def _int(key: str, default: int) -> int:
    """从环境变量读取整数，解析失败时返回默认值。"""
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


# 全局配置单例，项目中统一通过 CONFIG 访问
CONFIG = AppConfig(
    camera_index=_int("CAMERA_INDEX", 0),
    audio_sample_rate=_int("AUDIO_SAMPLE_RATE", 16000),
    audio_channels=_int("AUDIO_CHANNELS", 1),
    audio_block_duration_ms=_int("AUDIO_BLOCK_DURATION_MS", 30),
    max_context_rounds=_int("MAX_CONTEXT_ROUNDS", 5),
)
