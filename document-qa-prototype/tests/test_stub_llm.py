from app.llm.stub import get_stub_llm


def test_stub_with_context():
    llm = get_stub_llm()

    result = llm.generate(
        question="What is Kubernetes?",
        context=["Kubernetes orchestrates containers."],
    )

    assert result == "Kubernetes orchestrates containers."


def test_stub_without_context():
    llm = get_stub_llm()

    result = llm.generate(
        question="What is Kubernetes?",
        context=[],
    )

    assert result == "I don't know based on the provided document."
