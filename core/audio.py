from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import numpy as np
import sounddevice as sd
import soundfile as sf

from app.config import CONFIG


@dataclass
class AudioRecorder:
    """
    麦克风录音器。

    使用 sounddevice 以回调方式采集麦克风输入，
    支持开始/停止录音、保存为 WAV 文件和清空缓冲区。
    """

    sample_rate: int = CONFIG.audio_sample_rate
    channels: int = CONFIG.audio_channels
    # 录音帧缓冲区，每次回调追加一段音频数据
    frames: List[np.ndarray] = field(default_factory=list)
    is_recording: bool = False
    stream: sd.InputStream | None = None

    def start(self) -> bool:
        """
        开始录音。

        打开麦克风输入流，以回调方式实时采集音频帧。
        已在录音中时直接返回 True，启动失败时返回 False。
        """
        if self.is_recording:
            return True

        self.frames.clear()
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=self._callback,
            )
            self.stream.start()
            self.is_recording = True
            return True
        except Exception:
            self.stream = None
            self.is_recording = False
            return False

    def stop(self) -> None:
        """停止录音，关闭麦克风输入流并释放资源。"""
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            finally:
                self.stream = None
        self.is_recording = False

    def save(self, path: str | Path) -> Path:
        """
        将已录制的音频保存为 WAV 文件。

        :param path: 目标文件路径，父目录不存在时自动创建。
        :return: 实际写入的文件路径。
        """
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        sf.write(target, self.to_array(), self.sample_rate)
        return target

    def to_array(self) -> np.ndarray:
        """
        将帧缓冲区合并为连续的 numpy 数组。

        缓冲区为空时返回空数组，不会报错。
        """
        if not self.frames:
            return np.zeros((0, self.channels), dtype=np.int16)
        return np.concatenate(self.frames, axis=0)

    def clear(self) -> None:
        """清空帧缓冲区，释放内存，为下次录音做准备。"""
        self.frames.clear()

    def _callback(self, indata, frames, time, status) -> None:
        """sounddevice 音频回调，每隔一个 block 被调用一次。"""
        if status:
            # status 非零表示采集异常（如溢出），跳过本帧
            return
        self.frames.append(indata.copy())
