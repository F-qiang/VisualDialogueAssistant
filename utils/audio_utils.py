from pathlib import Path


def ensure_audio_path(path: str | Path) -> Path:
    return Path(path)
