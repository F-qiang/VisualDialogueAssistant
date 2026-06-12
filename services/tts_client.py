from pathlib import Path


class TTSClient:
    def synthesize(self, text: str, output_path: str | Path) -> Path:
        target = Path(output_path)
        target.write_bytes(b"")
        return target
