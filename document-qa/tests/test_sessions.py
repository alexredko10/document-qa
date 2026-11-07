"""Conversation context: history is persisted and fed back into the prompt."""

from fastapi.testclient import TestClient

K8S = "A pod is the smallest deployable unit in Kubernetes. Pods run containers."


def test_session_history_is_persisted_and_used(any_client: TestClient) -> None:
    any_client.post("/documents", json={"text": K8S})
    llm = any_client.app.state.services.llm  # type: ignore[attr-defined]

    first = any_client.post("/ask", json={"question": "What is a pod?"}).json()
    session_id = first["session_id"]

    second = any_client.post(
        "/ask", json={"question": "Do pods run containers?", "session_id": session_id}
    ).json()
    assert second["session_id"] == session_id
    # The previous turn reached the model as conversation context.
    assert "User: What is a pod?" in llm.last_user
    assert f"Assistant: {first['answer']}" in llm.last_user

    messages = any_client.get(f"/sessions/{session_id}/messages").json()
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
    assistant = messages[1]
    assert assistant["model_id"] == "mock"
    assert assistant["prompt_version"] == first["prompt_version"]
    # Sources are stored as references only, not as document text.
    assert assistant["sources"] and "text" not in assistant["sources"][0]


def test_history_window_is_bounded(make_client, backend) -> None:
    client = make_client(backend, history_messages=2)
    client.post("/documents", json={"text": K8S})
    llm = client.app.state.services.llm  # type: ignore[attr-defined]

    sid = client.post("/ask", json={"question": "What is a pod?"}).json()["session_id"]
    client.post("/ask", json={"question": "Pods run what?", "session_id": sid})
    client.post("/ask", json={"question": "Smallest unit?", "session_id": sid})

    assert "What is a pod?" not in llm.last_user
    assert "User: Pods run what?" in llm.last_user


def test_explicit_session_creation(client: TestClient) -> None:
    resp = client.post("/sessions")
    assert resp.status_code == 201
    sid = resp.json()["id"]
    assert client.get(f"/sessions/{sid}/messages").json() == []
