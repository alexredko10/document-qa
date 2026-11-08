from typing import Protocol


class LLMClient(Protocol):
    def generate(
        self,
        question: str,
        context: list[str],
    ) -> str:
        ...

    def generate_without_context(self, question: str) -> str:
        ...


class ContextFreeUnavailable(Exception):
    """The selected provider cannot generate without document context."""
