import base64
import os
from pathlib import Path

import requests


class ASRClient:
    """
    百度智能云短语音识别客户端。

    使用 client_credentials 方式换取 access_token，
    再将 WAV 文件以 base64 编码上传进行识别。
    token 在实例生命周期内缓存，避免重复请求。
    """

    TOKEN_URL = "https://openapi.baidu.com/oauth/2.0/token"
    ASR_URL = "https://vop.baidu.com/server_api"

    def __init__(self) -> None:
        # 从环境变量读取百度应用的 API Key 和 Secret Key
        self._api_key = os.getenv("ASR_API_KEY", "")
        self._secret_key = os.getenv("ASR_API_SECRET", "")
        self._token: str | None = None  # 缓存 access_token

    def _get_token(self) -> str:
        """
        获取百度 access_token。

        首次调用时请求接口并缓存结果，后续复用缓存。
        """
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
        """
        将 WAV 文件转为文字。

        :param audio_path: 本地 WAV 文件路径，需为 16000Hz 单声道。
        :return: 识别结果文字，识别失败或未配置 Key 时返回空字符串。
        """
        # 未配置 API Key 时跳过，不报错
        if not self._api_key or not self._secret_key:
            return ""
        try:
            audio_data = Path(audio_path).read_bytes()
            token = self._get_token()
            resp = requests.post(
                self.ASR_URL,
                json={
                    "format": "wav",
                    "rate": 16000,
                    "channel": 1,
                    "cuid": "visual_dialogue",  # 客户端标识，任意字符串即可
                    "token": token,
                    "speech": base64.b64encode(audio_data).decode(),
                    "len": len(audio_data),
                },
                timeout=15,
            )
            resp.raise_for_status()
            result = resp.json()
            # err_no 为 0 表示识别成功
            if result.get("err_no") == 0:
                return result["result"][0]
        except Exception:
            pass
        return ""
