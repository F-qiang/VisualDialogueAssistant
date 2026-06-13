from __future__ import annotations

import os
from typing import Iterable

import requests


class LLMClient:
    """
    智谱清言（GLM）文本对话客户端。

    通过 Bearer Token 鉴权调用 GLM 的 chat/completions 接口，
    支持传入完整的 messages 列表（含 system/user/assistant 角色）。
    """

    API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def __init__(self) -> None:
        # 从环境变量读取 API Key 和模型名称
        self._api_key = os.getenv("LLM_API_KEY", "")
        self._model = os.getenv("LLM_MODEL", "glm-4-flash")

    def chat(self, messages: Iterable[dict]) -> str:
        """
        发送对话请求并返回模型回复。

        :param messages: 消息列表，每项格式为 {"role": ..., "content": ...}
        :return: 模型回复文字，未配置 Key 或请求失败时返回空字符串。
        """
        # 未配置 API Key 时跳过，不报错
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
