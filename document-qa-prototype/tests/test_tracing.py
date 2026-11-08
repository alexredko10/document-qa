import io
import json

import httpx
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app import main
from app.llm.openrouter import OpenRouterLLM
from app.llm.provider import get_llm
from app.llm.stub import StubLLM
from app.observability import tracing
from app.observability.logging import logger
from app.rag.embedding_provider import HashEmbeddings, OpenRouterEmbeddings


def capture_logs():
    handler = next(h for h in logger.handlers if getattr(h, "_document_qa_handler", False))
    original = handler.stream
    stream = io.StringIO()
    handler.setStream(stream)
    return handler, original, stream


def test_spans_propagate_and_correlate_structured_logs(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": tracing.SERVICE_NAME}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(tracing, "get_tracer", lambda: provider.get_tracer(tracing.SERVICE_NAME))

    def provider_response(request):
        payload = json.loads(request.content)
        if request.url.path.endswith("/embeddings"):
            vectors = [
                {"index": index, "embedding": [1.0, 0.0]}
                for index, _ in enumerate(payload["input"])
            ]
            return httpx.Response(200, json={"model": "openai/text-embedding-3-small", "data": vectors})
        return httpx.Response(200, json={"choices": [{"message": {"content": "safe answer"}}]})

    handler, original, stream = capture_logs()
    with httpx.Client(transport=httpx.MockTransport(provider_response)) as provider_client:
        monkeypatch.setattr(main, "get_embedding_provider", lambda: OpenRouterEmbeddings("test-key", client=provider_client))
        main.app.dependency_overrides[get_llm] = lambda: OpenRouterLLM("test-key", client=provider_client)
        try:
            with TestClient(main.app) as client:
                uploaded = client.post(
                    "/documents",
                    headers={"X-Request-ID": "trace-upload"},
                    json={"text": "private document text for tracing"},
                )
                assert uploaded.status_code == 201
                document_id = uploaded.json()["document_id"]
                asked = client.post(
                    "/ask",
                    headers={"X-Request-ID": "trace-ask", "Authorization": "Bearer private-key"},
                    json={"document_id": document_id, "question": "private question"},
                )
                assert asked.status_code == 200
        finally:
            main.app.dependency_overrides.clear()
            handler.setStream(original)

    spans = exporter.get_finished_spans()
    ask_http = next(span for span in spans if span.name == "http.request" and span.attributes.get("http.route") == "/ask")
    children = [span for span in spans if span.context.trace_id == ask_http.context.trace_id]
    names = {span.name for span in children}
    assert {"embedding.request", "vector.retrieval", "llm.generation"} <= names
    assert all(span.parent.span_id == ask_http.context.span_id for span in children if span is not ask_http)

    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    ask_log = next(event for event in events if event["event"] == "http_request_completed" and event["request_id"] == "trace-ask")
    assert ask_log["trace_id"] == f"{ask_http.context.trace_id:032x}"
    assert ask_log["span_id"] == f"{ask_http.context.span_id:016x}"
    ask_events = [event for event in events if event["request_id"] == "trace-ask"]
    assert ask_events and {event["trace_id"] for event in ask_events} == {ask_log["trace_id"]}
    assert all({"trace_id", "span_id"} <= event.keys() for event in events)

    serialized = json.dumps([
        {"name": span.name, "attributes": dict(span.attributes), "events": [event.name for event in span.events]}
        for span in spans
    ]) + stream.getvalue()
    assert all(secret not in serialized for secret in ("private document text", "private question", "private-key", "safe answer", document_id))


def test_tracing_disabled_without_tempo_endpoint(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    monkeypatch.setattr(tracing, "get_tracer", lambda: trace.NoOpTracerProvider().get_tracer(tracing.SERVICE_NAME))
    monkeypatch.setattr(main, "get_embedding_provider", HashEmbeddings)
    assert tracing.configure_tracing() is False

    handler, original, stream = capture_logs()
    try:
        with TestClient(main.app) as client:
            response = client.post(
                "/documents",
                headers={"X-Request-ID": "no-tracing"},
                json={"text": "Kubernetes manages containers."},
            )
    finally:
        handler.setStream(original)

    assert response.status_code == 201
    event = next(json.loads(line) for line in stream.getvalue().splitlines() if "http_request_completed" in line)
    assert event["request_id"] == "no-tracing"
    assert event["trace_id"] is None and event["span_id"] is None


def test_tracing_setup_failure_does_not_break_api(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://tempo.invalid/v1/traces")
    monkeypatch.setattr(tracing, "_provider", None)
    monkeypatch.setattr(tracing, "get_tracer", lambda: trace.NoOpTracerProvider().get_tracer(tracing.SERVICE_NAME))
    monkeypatch.setattr(main, "get_embedding_provider", HashEmbeddings)
    main.app.dependency_overrides[get_llm] = lambda: StubLLM()

    def fail_exporter(**kwargs):
        raise RuntimeError("private exporter detail")

    monkeypatch.setattr(tracing, "OTLPSpanExporter", fail_exporter)
    handler, original, stream = capture_logs()
    try:
        assert tracing.configure_tracing() is False
        with TestClient(main.app) as client:
            uploaded = client.post("/documents", json={"text": "Kubernetes manages containers."})
            response = client.post(
                "/ask",
                headers={"X-Request-ID": "setup-failure"},
                json={"document_id": uploaded.json()["document_id"], "question": "Kubernetes manages containers"},
            )
    finally:
        main.app.dependency_overrides.clear()
        handler.setStream(original)

    assert uploaded.status_code == 201 and response.status_code == 200
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    setup = next(event for event in events if event["event"] == "tracing_setup_failed")
    assert setup["reason"] == "configuration_error"
    assert "private exporter detail" not in stream.getvalue()
