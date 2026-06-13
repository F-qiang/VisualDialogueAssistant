import base64
import os
from pathlib import Path

import requests


class ASRClient:
    """百度智能云短语音识别封装。"""

    TOKEN_URL = "https://openapi.baidu.com/oauth/2.0/token"
    ASR_URL = "https://vop.baidu.com/server_api"

    def __init__(self) -> None:
        self._api_key = os.getenv("ASR_API_KEY", "")
        self._secret_key = os.getenv("ASR_API_SECRET", "")
        self._token: str | None = None

    def _get_token(self) -> str:
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

    def transcribe(self, audio_path: str | Path) -> str:
        """将 WAV 文件转为文字，失败返回空字符串。"""
        if not self._api_key or not self._secret_key:
            return ""
        try:
            path = Path(audio_path)
            audio_data = path.read_bytes()
            token = self._get_token()
            resp = requests.post(
                self.ASR_URL,
                json={
                    "format": "wav",
                    "rate": 16000,
                    "channel": 1,
                    "cuid": "visual_dialogue",
                    "token": token,
                    "speech": base64.b64encode(audio_data).decode(),
                    "len": len(audio_data),
                },
                timeout=15,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("err_no") == 0:
                return result["result"][0]
        except Exception:
            pass
        return ""
