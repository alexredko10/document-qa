from fastapi.testclient import TestClient
from app.main import app, document_chunks

client = TestClient(app)


def test_create_document():
    response = client.post(
        "/documents",
        json={"text": "Kubernetes manages containers."},
    )

    assert response.status_code == 201
    assert "document_id" in response.json()
    assert response.json()["status"] == "accepted"


def test_empty_document():
    response = client.post(
        "/documents",
        json={"text": ""},
    )

    assert response.status_code == 422


def test_whitespace_document():
    response = client.post(
        "/documents",
        json={"text": "   "},
    )
    assert response.status_code == 422


def test_get_document():
    text = "Kubernetes manages containers."

    create_response = client.post(
        "/documents",
        json={"text": text},
    )
    assert create_response.status_code == 201
    document_id = create_response.json()["document_id"]
    get_response = client.get(f"/documents/{document_id}")
    assert get_response.status_code == 200
    assert get_response.json()["document_id"] == document_id
    assert get_response.json()["text"] == text


def test_oversized_document():
    response = client.post(
        "/documents",
        json={"text": "R" * 1_525_000},
    )
    assert response.status_code == 413


def test_document_not_found():
    response = client.get("/documents/unknown")
    assert response.status_code == 404

def test_document_is_chunked_on_upload():
    text = "A" * 500 + "B" * 100
    response = client.post(
        "/documents",
        json={"text": text},
    )
    assert response.status_code == 201
    document_id = response.json()["document_id"]
    chunks = document_chunks[document_id]
    assert chunks == [
        "A" * 500,
        "A" * 100 + "B" * 100,
    ]