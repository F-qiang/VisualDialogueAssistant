from dataclasses import dataclass, field
from typing import List


@dataclass
class ContextManager:
    """
    多轮对话上下文管理器。

    以 {"role": ..., "content": ...} 列表的形式保存对话历史，
    超出最大轮数后自动裁剪最旧的记录，保持上下文长度可控。
    """

    # 保留的最大对话轮数（一轮 = user + assistant 各一条）
    max_rounds: int = 5
    history: List[dict] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        """
        追加一条对话记录。

        超出 max_rounds * 2 条后，自动裁剪最旧的记录。
        :param role: 角色，通常为 "user" 或 "assistant"
        :param content: 消息内容
        """
        self.history.append({"role": role, "content": content})
        max_items = self.max_rounds * 2  # 每轮包含 user + assistant 两条
        if len(self.history) > max_items:
            self.history = self.history[-max_items:]

    def get(self) -> list[dict]:
        """返回当前完整的对话历史副本。"""
        return list(self.history)

    def clear(self) -> None:
        """清空所有对话历史。"""
        self.history.clear()
