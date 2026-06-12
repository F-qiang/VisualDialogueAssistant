from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "AI视觉对话助手"
    camera_index: int = 0
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    audio_block_duration_ms: int = 30
    max_context_rounds: int = 5


CONFIG = AppConfig()
