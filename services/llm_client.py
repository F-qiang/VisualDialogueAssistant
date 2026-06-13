import os
from typing import Iterable

import requests


class LLMClient:
    """智谱清言（GLM）文本对话封装。"""

    API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def __init__(self) -> None:
        self._api_key = os.getenv("LLM_API_KEY", "")
        self._model = os.getenv("LLM_MODEL", "glm-4-flash")

    def chat(self, messages: Iterable[dict]) -> str:
        """发送对话请求，失败返回空字符串。"""
        if not self._api_key:
            return ""
        try:
            resp = requests.post(
                self.API_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": list(messages),
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            return ""
