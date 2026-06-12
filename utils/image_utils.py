from pathlib import Path


def ensure_image_path(path: str | Path) -> Path:
    return Path(path)
