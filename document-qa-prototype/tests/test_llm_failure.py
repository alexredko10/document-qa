from fastapi.testclient import TestClient

from app.main import app
from app.llm.provider import get_llm
from app.llm.openrouter import LLMProviderError


class FailingLLM:
    def generate(
        self,
        question: str,
        context: list[str],
    ) -> str:
        raise LLMProviderError(
            "rate_limited",
            retry_after="60",
        )


def test_llm_failure_returns_503():
    app.dependency_overrides[get_llm] = lambda: FailingLLM()

    try:
        with TestClient(app) as client:
            created = client.post(
                "/documents",
                json={"text": "Kubernetes manages containers."},
            )

            document_id = created.json()["document_id"]

            response = client.post(
                "/ask",
                json={
                    "document_id": document_id,
                    "question": "Kubernetes manages containers",
                },
            )

            assert response.status_code == 503
            assert response.headers["Retry-After"] == "60"
            assert response.json()["detail"] == "LLM provider unavailable"

    finally:
        app.dependency_overrides.clear()
