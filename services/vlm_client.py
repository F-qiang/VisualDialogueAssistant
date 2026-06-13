from __future__ import annotations

import base64
import os
from typing import Iterable

import requests


class VLMClient:
    """
    智谱清言多模态视觉语言模型客户端（GLM-4V）。

    将图像（base64 编码）和文字问题一起发送给 VLM，
    返回包含图像理解内容的回答。
    """

    API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def __init__(self) -> None:
        # VLM 与 LLM 共用同一套 API Key，从环境变量读取
        self._api_key = os.getenv("LLM_API_KEY", "")
        self._model = os.getenv("VLM_MODEL", "glm-4v-flash")

    def chat_with_image(
        self,
        image_bytes: bytes,
        question: str,
        history: Iterable[dict] | None = None,
    ) -> str:
        """
        发送带图像的多模态问答请求。

        :param image_bytes: JPEG 格式的图像字节，发送前已在调用侧压缩。
        :param question: 用户当前提问文字。
        :param history: 历史对话列表（不含 system），用于多轮视觉追问。
        :return: 模型回复文字，失败时返回空字符串。
        """
        if not self._api_key:
            return ""
        try:
            # 将图像编码为 base64 字符串
            b64_image = base64.b64encode(image_bytes).decode()

            # 构造 messages：历史记录 + 当前带图问题
            messages = list(history or [])
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                    },
                    {"type": "text", "text": question},
                ],
            })

            resp = requests.post(
                self.API_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self._model, "messages": messages},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            return ""
