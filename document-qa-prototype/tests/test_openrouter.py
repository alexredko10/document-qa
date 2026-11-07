import httpx
import pytest

from app.llm.openrouter import OpenRouterLLM, LLMProviderError


def test_openrouter_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"

        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "Kubernetes manages containers."
                        }
                    }
                ]
            },
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler)
    ) as client:
        llm = OpenRouterLLM(
            api_key="test-key",
            client=client,
        )

        result = llm.generate(
            question="What manages containers?",
            context=["Kubernetes manages containers."],
        )

    assert result == "Kubernetes manages containers."


def test_openrouter_rate_limited():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"Retry-After": "60"},
            json={"error": {"message": "Rate limit exceeded"}},
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler)
    ) as client:
        llm = OpenRouterLLM(
            api_key="test-key",
            client=client,
        )

        with pytest.raises(LLMProviderError) as exc:
            llm.generate(
                question="What is Kubernetes?",
                context=["Kubernetes is a platform."],
            )

    assert exc.value.reason == "rate_limited"
    assert exc.value.retry_after == "60"