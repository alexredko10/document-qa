from app.llm.base import LLMClient


class StubLLM:
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