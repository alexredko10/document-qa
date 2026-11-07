"""Mock LLM: deterministic extractive answers without an API key."""

import re

from app.llm.base import LLMClient, LLMResponse
from app.rag.guard import DONT_KNOW

_EXCERPT = re.compile(r"^\[(\d+)\] (.+?)(?=\n\n\[\d+\] |\n\nConversation so far:|\Z)", re.M | re.S)
_QUESTION = re.compile(r"^Question: (.+)$", re.M)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[a-z0-9]+")


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if len(w) > 2}


class MockLLM(LLMClient):
    """Returns the context sentence that shares the most words with the question,
    citing its excerpt number. Behaves like a cautious extractive reader.

    Keeps the last prompt it received so tests can assert on what the service
    sent (history, context) without patching.
    """

    model_id = "mock"

    def __init__(self) -> None:
        self.last_system: str | None = None
        self.last_user: str | None = None
        self.calls = 0

    async def complete(self, system: str, user: str) -> LLMResponse:
        self.calls += 1
        self.last_system, self.last_user = system, user
        text = self._extract(user)
        return LLMResponse(
            text=text,
            input_tokens=max(1, (len(system) + len(user)) // 4),
            output_tokens=max(1, len(text) // 4),
        )

    @staticmethod
    def _extract(user: str) -> str:
        q = _QUESTION.search(user)
        question_words = _words(q.group(1)) if q else set()
        best: tuple[int, str, str] | None = None  # (overlap, sentence, excerpt number)
        for number, body in _EXCERPT.findall(user):
            for sentence in _SENTENCE_SPLIT.split(body.strip()):
                overlap = len(question_words & _words(sentence))
                if best is None or overlap > best[0]:
                    best = (overlap, sentence.strip(), number)
        if best is None or best[0] == 0:
            return DONT_KNOW
        return f"{best[1]} [{best[2]}]"
