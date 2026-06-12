from enum import Enum


class AppState(str, Enum):
    IDLE = "idle"
    RECORDING = "recording"
    THINKING = "thinking"
    SPEAKING = "speaking"
