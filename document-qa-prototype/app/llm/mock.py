class MockLLM:
    def generate(
        self,
        question: str,
        context: list[str],
    ) -> str:
        if not context:
            return "I don't know based on the provided document."

        return context[0]