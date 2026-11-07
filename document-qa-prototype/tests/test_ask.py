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
