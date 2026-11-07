from typing import Protocol


class LLMClient(Protocol):
    def generate(
        self,
        question: str,
        context: list[str],
    ) -> str:
        ...