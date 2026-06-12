from dataclasses import dataclass, field
from typing import List


@dataclass
class ContextManager:
    max_rounds: int = 5
    history: List[dict] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        max_items = self.max_rounds * 2
        if len(self.history) > max_items:
            self.history = self.history[-max_items:]

    def get(self) -> list[dict]:
        return list(self.history)

    def clear(self) -> None:
        self.history.clear()
