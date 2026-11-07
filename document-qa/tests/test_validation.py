"""Input limits (413), empty input (422), unknown ids (404)."""

import uuid

from fastapi.testclient import TestClient

from tests.conftest import MakeClient


def test_document_over_byte_limit_returns_413(make_client: MakeClient) -> None:
    client = make_client(max_document_bytes=1_000)
    resp = client.post("/documents", json={"text": "a" * 1_001})
    assert resp.status_code == 413
    assert "limit is 1000 bytes" in resp.json()["detail"]


def test_limit_counts_bytes_not_characters(make_client: MakeClient) -> None:
    client = make_client(max_document_bytes=1_000)
    # 600 characters, 1,200 bytes in UTF-8.
    resp = client.post("/documents", json={"text": "я" * 600})
    assert resp.status_code == 413


def test_oversized_body_rejected_before_parsing(make_client: MakeClient) -> None:
    client = make_client(max_document_bytes=1_000)
    resp = client.post("/documents", json={"text": "a" * 200_000})
    assert resp.status_code == 413
    assert "body" in resp.json()["detail"].lower()


def test_question_over_byte_limit_returns_413(client: TestClient) -> None:
    resp = client.post("/ask", json={"question": "pod " * 1_000})
    assert resp.status_code == 413


def test_empty_and_blank_inputs_return_422(client: TestClient) -> None:
    assert client.post("/documents", json={"text": ""}).status_code == 422
    assert client.post("/documents", json={"text": "   \n  "}).status_code == 422
    assert client.post("/ask", json={"question": "   "}).status_code == 422


def test_malformed_ids_return_422(client: TestClient) -> None:
    assert client.post("/documents/not-a-uuid/approve").status_code == 422
    assert client.post("/ask", json={"question": "q", "session_id": "nope"}).status_code == 422


def test_unknown_ids_return_404(client: TestClient) -> None:
    missing = str(uuid.uuid4())
    assert client.post(f"/documents/{missing}/approve").status_code == 404
    assert client.get(f"/documents/{missing}").status_code == 404
    assert client.get(f"/sessions/{missing}/messages").status_code == 404
    assert client.post("/ask", json={"question": "q", "session_id": missing}).status_code == 404
    resp = client.post("/ask", json={"question": "q", "document_ids": [missing]})
    assert resp.status_code == 404


def test_health_probes(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}
