from dataclasses import dataclass, field
from typing import List


@dataclass
class ContextManager:
    """
    多轮对话上下文管理器。

    以 {"role": ..., "content": ...} 列表的形式保存对话历史，
    超出最大轮数后自动裁剪最旧的记录，保持上下文长度可控。
    PR12：超出 max_rounds 时自动摘要压缩老轮次。
    """

    # 保留的最大对话轮数（一轮 = user + assistant 各一条）
    max_rounds: int = 5
    history: List[dict] = field(default_factory=list)
    _summary_count: int = 0  # 摘要次数统计

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
            # PR12：自动触发摘要压缩
            self._auto_summarize()

    def _auto_summarize(self) -> None:
        """
        当历史超出 max_rounds 时，摘要最旧的对话。
        
        将前两轮（4 条消息）压缩成一条背景摘要消息。
        """
        max_items = self.max_rounds * 2
        if len(self.history) <= max_items:
            return
        
        # 取出前 4 条（最旧的两轮）
        old_rounds = self.history[:4]
        
        # 构建摘要提示词
        old_text = "\n".join([f"{m['role']}: {m['content']}" for m in old_rounds])
        
        # 简单摘要：提取关键词
        # 实际场景可调用 LLM 做更好的摘要，但为了减少 API 调用，这里用简单策略
        summary = self._simple_summarize(old_text)
        
        # 用摘要消息替换前 4 条消息
        self.history = [
            {"role": "system", "content": f"背景：{summary}"}
        ] + self.history[4:]
        
        self._summary_count += 1

    def _simple_summarize(self, text: str) -> str:
        """
        简单摘要：截取前 100 字符 + 省略号。
        
        实际应用可改为调用 LLM 做更精细的摘要。
        """
        if len(text) > 100:
            return text[:100] + "..."
        return text

    def get(self) -> list[dict]:
        """返回当前完整的对话历史副本。"""
        return list(self.history)

    def get_summary_count(self) -> int:
        """返回摘要压缩次数。"""
        return self._summary_count

    def clear(self) -> None:
        """清空所有对话历史。"""
        self.history.clear()
        self._summary_count = 0

