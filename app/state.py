from enum import Enum


class AppState(str, Enum):
    """
    系统运行状态枚举。

    用于标记当前系统处于哪个阶段，便于界面状态提示和逻辑互斥控制。
    - IDLE：空闲，等待用户输入
    - RECORDING：正在录音
    - THINKING：ASR 识别或 LLM 推理中
    - SPEAKING：正在播报语音回复
    """

    IDLE = "idle"
    RECORDING = "recording"
    THINKING = "thinking"
    SPEAKING = "speaking"
