import json
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app import main
from app.llm.openrouter import OpenRouterLLM
from app.llm.provider import get_llm
from app.main import app


def test_default_context_and_stub_rejection():
    with TestClient(app) as client:
        doc = client.post('/documents', json={'text': 'Kubernetes manages containers.'}).json()['document_id']
        rag = client.post('/ask', json={'document_id': doc, 'question': 'Kubernetes manages containers'})
        assert rag.status_code == 200 and rag.json()['use_context'] is True
        assert rag.json()['source_chunks'] and rag.json()['llm']['actual_model'] == 'stub'
        no_rag = client.post('/ask', json={'question': 'What is Kubernetes?', 'use_context': False})
        assert no_rag.status_code == 501 and 'real generative provider' in no_rag.json()['detail']
        assert no_rag.headers['x-request-id']


def test_no_context_skips_retrieval_and_instruments(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail('context-free request accessed retrieval')
    monkeypatch.setattr(main, 'embed_text', fail)
    monkeypatch.setattr(main, 'search_vectors', fail)
    monkeypatch.setattr(main, 'has_relevant_context', fail)
    payloads = []
    def handler(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json={'model': 'provider/real', 'usage': {'prompt_tokens': 7, 'completion_tokens': 2}, 'choices': [{'message': {'content': 'general answer'}}]})
    labels = {'provider': 'openrouter', 'outcome': 'success'}
    before = REGISTRY.get_sample_value('llm_calls_total', labels) or 0
    duration = REGISTRY.get_sample_value('llm_call_duration_seconds_count', {'provider': 'openrouter'}) or 0
    tokens = REGISTRY.get_sample_value('llm_tokens_total', {'provider': 'openrouter', 'direction': 'input'}) or 0
    with httpx.Client(transport=httpx.MockTransport(handler)) as provider:
        app.dependency_overrides[get_llm] = lambda: OpenRouterLLM('test-key', model='test/model', client=provider)
        try:
            with TestClient(app) as client:
                response = client.post('/ask', json={'question': 'What is Kubernetes?', 'document_id': 'secret-doc-id', 'use_context': False}, headers={'X-Request-ID': 'general-1'})
        finally:
            app.dependency_overrides.clear()
    assert response.status_code == 200 and response.headers['x-request-id'] == 'general-1'
    data = response.json()
    assert data['answer'] == 'general answer' and data['source_chunks'] == [] and data['use_context'] is False
    assert data['llm']['invoked'] and data['llm']['requested_model'] == 'test/model'
    assert data['llm']['actual_model'] == 'provider/real' and data['llm']['input_tokens'] == 7 and data['llm']['duration_ms'] >= 0
    assert payloads[0]['messages'][1] == {'role': 'user', 'content': 'What is Kubernetes?'}
    assert 'secret-doc-id' not in json.dumps(payloads) and 'document' not in json.dumps(payloads).lower()
    assert REGISTRY.get_sample_value('llm_calls_total', labels) == before + 1
    assert REGISTRY.get_sample_value('llm_call_duration_seconds_count', {'provider': 'openrouter'}) == duration + 1
    assert REGISTRY.get_sample_value('llm_tokens_total', {'provider': 'openrouter', 'direction': 'input'}) == tokens + 7


def test_both_modes_and_concurrent_metadata():
    def handler(request):
        payload = json.loads(request.content)
        question = payload['messages'][1]['content']
        number = int(question.rsplit('marker', 1)[1])
        return httpx.Response(200, json={'model': f'provider/model-{number}', 'usage': {'prompt_tokens': number}, 'choices': [{'message': {'content': f'answer-{number}'}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as provider:
        app.dependency_overrides[get_llm] = lambda: OpenRouterLLM('test-key', model='same/model', client=provider)
        try:
            with TestClient(app) as client:
                doc = client.post('/documents', json={'text': 'Kubernetes manages containers.'}).json()['document_id']
                def run(i):
                    return client.post('/ask', headers={'X-Request-ID': f'compare-{i}'}, json={'document_id': doc, 'question': f'Kubernetes manages containers marker{i}', 'use_context': bool(i % 2)})
                with ThreadPoolExecutor(max_workers=8) as pool:
                    responses = list(pool.map(run, range(1, 13)))
        finally:
            app.dependency_overrides.clear()
    for i, response in enumerate(responses, 1):
        data = response.json()
        assert response.status_code == 200 and response.headers['x-request-id'] == f'compare-{i}'
        assert data['use_context'] == bool(i % 2)
        assert bool(data['source_chunks']) == bool(i % 2)
        assert data['llm']['requested_model'] == 'same/model'
        assert data['llm']['actual_model'] == f'provider/model-{i}' and data['llm']['input_tokens'] == i


def test_context_free_provider_error_is_safe():
    def handler(request):
        return httpx.Response(429, headers={'Retry-After': '5'}, json={'error': 'secret'})
    with httpx.Client(transport=httpx.MockTransport(handler)) as provider:
        app.dependency_overrides[get_llm] = lambda: OpenRouterLLM('test-key', client=provider)
        try:
            with TestClient(app) as client:
                response = client.post('/ask', json={'question': 'question', 'use_context': False})
        finally:
            app.dependency_overrides.clear()
    assert response.status_code == 503 and response.headers['retry-after'] == '5'
    assert 'secret' not in response.text


def test_both_modes_use_same_generation_settings_and_emit_correlated_logs():
    import io
    from app.observability.logging import logger

    payloads = []
    def handler(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json={'model': 'actual/model', 'choices': [{'message': {'content': 'answer'}}]})
    stream = io.StringIO()
    log_handler = next(h for h in logger.handlers if getattr(h, '_document_qa_handler', False))
    original = log_handler.stream
    log_handler.setStream(stream)
    try:
        with httpx.Client(transport=httpx.MockTransport(handler)) as provider:
            app.dependency_overrides[get_llm] = lambda: OpenRouterLLM('test-key', model='same/model', client=provider)
            try:
                with TestClient(app) as client:
                    doc = client.post('/documents', json={'text': 'Kubernetes manages containers.'}).json()['document_id']
                    rag = client.post('/ask', headers={'X-Request-ID': 'rag-request'}, json={'document_id': doc, 'question': 'Kubernetes manages containers'})
                    plain = client.post('/ask', headers={'X-Request-ID': 'plain-request'}, json={'question': 'Kubernetes manages containers', 'use_context': False})
            finally:
                app.dependency_overrides.clear()
    finally:
        log_handler.setStream(original)
    assert rag.status_code == plain.status_code == 200
    assert rag.headers['x-request-id'] == 'rag-request' and plain.headers['x-request-id'] == 'plain-request'
    assert [(p['model'], p['temperature']) for p in payloads] == [('same/model', 0), ('same/model', 0)]
    assert 'Document excerpts:' in payloads[0]['messages'][1]['content']
    assert payloads[1]['messages'][1]['content'] == 'Kubernetes manages containers'
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    for request_id in ('rag-request', 'plain-request'):
        assert any(e['event'] == 'llm_call_completed' and e['request_id'] == request_id and e['outcome'] == 'success' for e in events)
        assert any(e['event'] == 'http_request_completed' and e['request_id'] == request_id for e in events)


@pytest.mark.parametrize('document_id', [None, '', '   '])
@pytest.mark.parametrize('explicit_mode', [False, True])
def test_context_requires_nonempty_document_id(document_id, explicit_mode):
    payload = {'question': 'question'}
    if document_id is not None:
        payload['document_id'] = document_id
    if explicit_mode:
        payload['use_context'] = True
    with TestClient(app) as client:
        response = client.post('/ask', json=payload)
    assert response.status_code == 422


def test_context_free_does_not_require_document_id():
    with TestClient(app) as client:
        for document_id in (None, '', '   '):
            response = client.post('/ask', json={'question': 'question', 'use_context': False, 'document_id': document_id})
            assert response.status_code == 501


def test_ask_mode_log_is_correlated_bounded_and_private():
    import io
    from app.observability.logging import logger

    stream = io.StringIO()
    handler = next(h for h in logger.handlers if getattr(h, '_document_qa_handler', False))
    original = handler.stream
    handler.setStream(stream)
    try:
        with TestClient(app) as client:
            created = client.post('/documents', json={'text': 'private-document Kubernetes manages containers.'})
            doc_id = created.json()['document_id']
            rag = client.post('/ask', headers={'X-Request-ID': 'rag-id', 'Authorization': 'Bearer private-credential'}, json={'document_id': doc_id, 'question': 'private-question Kubernetes manages containers'})
            plain = client.post('/ask', headers={'X-Request-ID': 'plain-id'}, json={'question': 'private-question', 'use_context': False})
            missing = client.post('/ask', headers={'X-Request-ID': 'missing-id'}, json={'document_id': 'missing-secret-document', 'question': 'private-question'})
            invalid = client.post('/ask', headers={'X-Request-ID': 'invalid-id'}, json={'question': 'private-question'})
    finally:
        handler.setStream(original)
    assert rag.status_code == 200 and plain.status_code == 501 and missing.status_code == 404 and invalid.status_code == 422
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    mode_events = [e for e in events if e['event'] == 'ask_request_received']
    assert [(e['request_id'], e['context_mode']) for e in mode_events] == [('rag-id', 'rag'), ('plain-id', 'no_rag'), ('missing-id', 'rag')]
    assert all(set(event) == {'timestamp', 'level', 'event', 'request_id', 'context_mode', 'trace_id', 'span_id'} for event in mode_events)
    for secret in ('private-document', 'private-credential', 'private-question', 'missing-secret-document', doc_id):
        assert secret not in stream.getvalue()
