from core.context import ContextManager


class DialoguePipeline:
    def __init__(self, max_rounds: int = 5) -> None:
        self.context = ContextManager(max_rounds=max_rounds)

    def add_user_message(self, text: str) -> None:
        self.context.add("user", text)

    def add_assistant_message(self, text: str) -> None:
        self.context.add("assistant", text)
