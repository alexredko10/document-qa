"""LLMClient interface and response types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int


class LLMClient(ABC):
    model_id: str = "unknown"

    @abstractmethod
    async def complete(self, system: str, user: str) -> LLMResponse:
        """Single-turn completion. Stage 2 adds a tool-calling variant."""
