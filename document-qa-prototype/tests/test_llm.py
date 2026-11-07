from app.llm.mock import MockLLM


def test_mock_llm_with_context():
    llm = MockLLM()

    answer = llm.generate(
        question="What manages containers?",
        context=["Kubernetes manages containers."],
    )

    assert answer == "Kubernetes manages containers."


def test_mock_llm_without_context():
    llm = MockLLM()

    answer = llm.generate(
        question="What is the capital of Mars?",
        context=[],
    )

    assert answer == "I don't know based on the provided document."