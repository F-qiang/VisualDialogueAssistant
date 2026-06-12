from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class AudioBuffer:
    frames: List[bytes] = field(default_factory=list)

    def clear(self) -> None:
        self.frames.clear()

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.write_bytes(b"".join(self.frames))
        return target
