from __future__ import annotations

import os
import tempfile
from pathlib import Path

import requests

try:
    import pyttsx3
except Exception:  # pragma: no cover
    pyttsx3 = None


class TTSClient:
    """
    百度智能云 TTS 语音合成客户端。

    将文本转换为 MP3 音频文件，供界面层通过 Qt 播放器播放。
    token 在实例生命周期内缓存，避免重复请求。
    """

    TOKEN_URL = "https://openapi.baidu.com/oauth/2.0/token"
    TTS_URL = "https://tsn.baidu.com/text2audio"

    def __init__(self) -> None:
        # 与 ASR 共用同一套百度 API Key / Secret Key
        self._api_key = os.getenv("ASR_API_KEY", "")
        self._secret_key = os.getenv("ASR_API_SECRET", "")
        self._token: str | None = None

    def _get_token(self) -> str:
        """获取 access_token，首次请求后缓存复用。"""
        if self._token:
            return self._token
        resp = requests.post(
            self.TOKEN_URL,
            params={
                "grant_type": "client_credentials",
                "client_id": self._api_key,
                "client_secret": self._secret_key,
            },
            timeout=10,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    @staticmethod
    def _normalize_speed(speed: float) -> int:
        """将倍数转换为百度 API 语速参数。"""
        return max(0, min(15, int(round(5 * speed))))

    @staticmethod
    def _normalize_volume(volume: float) -> int:
        """将百分比转换为百度 API 音量参数。"""
        return max(0, min(15, int(round(volume * 15 / 100))))

    def synthesize(self, text: str, output_path: str | Path | None = None, 
                   speed: float = 1.0, volume: float = 100) -> Path:
        """
        将文本合成为 WAV 音频并保存到文件。

        :param text: 待合成文字，建议不超过 1024 字节。
        :param output_path: 目标文件路径，为 None 时写入系统临时目录。
        :param speed: 语速倍数（0.5-2.0），默认 1.0
        :param volume: 音量百分比（0-100），默认 100
        :return: 已保存的音频文件路径，失败时返回空文件路径。
        """
        target = Path(output_path or tempfile.mktemp(suffix=".wav"))
        target.parent.mkdir(parents=True, exist_ok=True)
        if pyttsx3 is not None:
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", int(180 * speed))
                engine.setProperty("volume", max(0.0, min(1.0, volume / 100.0)))
                engine.save_to_file(text, str(target))
                engine.runAndWait()
                if target.stat().st_size > 0:
                    return target
            except Exception:
                pass
        if not self._api_key or not self._secret_key:
            target.write_bytes(b"")
            return target
        try:
            token = self._get_token()
            resp = requests.post(
                self.TTS_URL,
                data={
                    "tex": text,
                    "tok": token,
                    "cuid": "visual_dialogue",
                    "ctp": 1,
                    "lan": "zh",
                    "spd": self._normalize_speed(speed),
                    "pit": 5,
                    "vol": self._normalize_volume(volume),
                    "per": 0,
                    "aue": 6,
                },
                timeout=15,
            )
            if "audio" in resp.headers.get("Content-Type", ""):
                target.write_bytes(resp.content)
            else:
                target.write_bytes(b"")
        except Exception:
            target.write_bytes(b"")
        return target
