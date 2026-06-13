import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "AI视觉对话助手"
    camera_index: int = 0
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    audio_block_duration_ms: int = 30
    max_context_rounds: int = 5


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


CONFIG = AppConfig(
    camera_index=_int("CAMERA_INDEX", 0),
    audio_sample_rate=_int("AUDIO_SAMPLE_RATE", 16000),
    audio_channels=_int("AUDIO_CHANNELS", 1),
    audio_block_duration_ms=_int("AUDIO_BLOCK_DURATION_MS", 30),
    max_context_rounds=_int("MAX_CONTEXT_ROUNDS", 5),
)
