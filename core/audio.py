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
    sample_rate: int = CONFIG.audio_sample_rate
    channels: int = CONFIG.audio_channels
    frames: List[np.ndarray] = field(default_factory=list)
    is_recording: bool = False
    stream: sd.InputStream | None = None

    def start(self) -> bool:
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
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            finally:
                self.stream = None
        self.is_recording = False

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        audio = self.to_array()
        sf.write(target, audio, self.sample_rate)
        return target

    def to_array(self) -> np.ndarray:
        if not self.frames:
            return np.zeros((0, self.channels), dtype=np.int16)
        return np.concatenate(self.frames, axis=0)

    def clear(self) -> None:
        self.frames.clear()

    def _callback(self, indata, frames, time, status) -> None:
        if status:
            return
        self.frames.append(indata.copy())
