"""Chunking, approval gating, retrieval and the 'I don't know' guard.

API tests use `any_client`, so each runs against both the memory and the
Postgres backend.
"""

import pytest
from fastapi.testclient import TestClient

from app.rag.chunker import TextChunker
from app.rag.guard import DONT_KNOW
from tests.conftest import MakeClient

K8S = (
    "Kubernetes schedules containers onto nodes. "
    "A pod is the smallest deployable unit in Kubernetes. "
    "ReplicaSets keep a stable number of pod replicas running."
)
COFFEE = (
    "Espresso is brewed by forcing hot water through finely ground coffee. "
    "A cappuccino adds steamed milk foam to espresso."
)


def upload(client: TestClient, text: str, title: str | None = None) -> dict:
    resp = client.post("/documents", json={"text": text, "title": title})
    assert resp.status_code == 201, resp.text
    return resp.json()


# ------------------------------------------------------------------ chunker


def test_chunker_respects_size_and_overlap() -> None:
    text = " ".join(f"word{i}" for i in range(500))
    chunks = TextChunker(chunk_size=200, overlap=40).chunk(text)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
    # Overlap: the start of each chunk repeats the tail of the previous one.
    assert chunks[1].split()[0] in chunks[0]


def test_chunker_rejects_bad_config() -> None:
    with pytest.raises(ValueError):
        TextChunker(chunk_size=100, overlap=100)


# ------------------------------------------------------------------ answering


def test_answer_with_sources(any_client: TestClient) -> None:
    doc = upload(any_client, K8S, title="k8s-101")
    assert doc["status"] == "approved"  # AUTO_APPROVE defaults to true

    resp = any_client.post("/ask", json={"question": "What is a pod in Kubernetes?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["grounded"] is True
    assert "pod" in body["answer"].lower()
    assert body["sources"][0]["document_id"] == doc["id"]
    assert body["model_id"] == "mock"
    assert len(body["prompt_version"]) == 12


def test_unanswerable_question_is_refused_without_calling_llm(any_client: TestClient) -> None:
    upload(any_client, K8S)
    llm = any_client.app.state.services.llm  # type: ignore[attr-defined]

    resp = any_client.post("/ask", json={"question": "What is the boiling point of mercury?"})
    body = resp.json()
    assert body["answer"] == DONT_KNOW
    assert body["grounded"] is False
    assert body["sources"] == []
    assert llm.calls == 0


def test_document_ids_restrict_retrieval(any_client: TestClient) -> None:
    k8s = upload(any_client, K8S)
    upload(any_client, COFFEE)

    # Coffee question, but scoped to the Kubernetes document -> nothing relevant.
    resp = any_client.post(
        "/ask", json={"question": "How is espresso brewed?", "document_ids": [k8s["id"]]}
    )
    assert resp.json()["answer"] == DONT_KNOW

    resp = any_client.post("/ask", json={"question": "How is espresso brewed?"})
    assert "espresso" in resp.json()["answer"].lower()


# ------------------------------------------------------------------ approval gate


def test_pending_documents_are_invisible_until_approved(make_client: MakeClient, backend) -> None:
    client = make_client(backend, auto_approve=False)
    doc = upload(client, K8S)
    assert doc["status"] == "pending"

    resp = client.post("/ask", json={"question": "What is a pod?"})
    assert resp.json()["answer"] == DONT_KNOW

    resp = client.post("/ask", json={"question": "What is a pod?", "document_ids": [doc["id"]]})
    assert resp.status_code == 409

    approved = client.post(f"/documents/{doc['id']}/approve").json()
    assert approved["status"] == "approved"
    assert approved["approved_at"] is not None
    # Idempotent.
    assert client.post(f"/documents/{doc['id']}/approve").status_code == 200

    resp = client.post("/ask", json={"question": "What is a pod?"})
    assert resp.json()["grounded"] is True


def test_list_documents_filters_by_status(make_client: MakeClient, backend) -> None:
    client = make_client(backend, auto_approve=False)
    a = upload(client, K8S)
    upload(client, COFFEE)
    client.post(f"/documents/{a['id']}/approve")

    pending = client.get("/documents", params={"status": "pending"}).json()
    approved = client.get("/documents", params={"status": "approved"}).json()
    assert [d["id"] for d in approved] == [a["id"]]
    assert len(pending) == 1
    assert len(client.get("/documents").json()) == 2


def test_model_refusal_is_not_reported_as_grounded(any_client: TestClient) -> None:
    from app.llm.base import LLMResponse

    upload(any_client, K8S)
    llm = any_client.app.state.services.llm  # type: ignore[attr-defined]

    async def refuse(system: str, user: str) -> LLMResponse:
        return LLMResponse(text=f'"{DONT_KNOW}"', input_tokens=10, output_tokens=5)

    llm.complete = refuse
    body = any_client.post("/ask", json={"question": "What is a pod?"}).json()
    assert body["answer"] == DONT_KNOW
    assert body["grounded"] is False
    assert body["sources"] == []
