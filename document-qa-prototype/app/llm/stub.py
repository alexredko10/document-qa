from app.llm.base import LLMClient
from app.observability.llm import instrument_llm


class StubLLM:
    @instrument_llm("stub")
    def generate(
        self,
        question: str,
        context: list[str],
    ) -> str:
        if not context:
            return "I don't know based on the provided document."

        return context[0]


def get_stub_llm() -> LLMClient:
    return StubLLM()