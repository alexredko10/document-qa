from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ask_retrieves_document_chunks():
    text = "Kubernetes manages containers."

    created = client.post(
        "/documents",
        json={"text": text},
    )

    assert created.status_code == 201
    document_id = created.json()["document_id"]

    response = client.post(
        "/ask",
        json={
            "document_id": document_id,
            "question": "Kubernetes manages containers",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["answer"] == text
    assert len(data["source_chunks"]) >= 1
    assert data["source_chunks"][0]["text"] == text

def test_ask_refuses_unsupported_question(monkeypatch):
    from app import main
    from app.rag.retriever import ScoredChunk

    # intentionally send errored retrieval:
    # not relevant chunk got a higher score.
    monkeypatch.setattr(
        main,
        "search_vectors",
        lambda **kwargs: [
            ScoredChunk(
                index=0,
                text="Kubernetes manages containers.",
                score=0.99,
            )
        ],
    )

    created = client.post(
        "/documents",
        json={"text": "Kubernetes manages containers."},
    )

    response = client.post(
        "/ask",
        json={
            "document_id": created.json()["document_id"],
            "question": "How many moons does Jupiter have?",
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == (
        "I don't know based on the provided document."
    )