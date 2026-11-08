import io
import json
import re
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient

from app.llm.openrouter import LLMProviderError, OpenRouterLLM
from app.llm.provider import get_llm
from app.main import app
from app.observability.logging import configure_logger, logger, request_id_context


@pytest.fixture
def logs():
    stream = io.StringIO()
    handler = next(h for h in logger.handlers if getattr(h, '_document_qa_handler', False))
    original = handler.stream
    handler.setStream(stream)
    yield lambda: [json.loads(line) for line in stream.getvalue().splitlines()]
    handler.setStream(original)


def test_request_correlation_and_privacy(logs):
    with TestClient(app) as client:
        assert re.fullmatch(r'[A-Za-z0-9_-]{1,64}', client.get('/healthz').headers['x-request-id'])
        created = client.post('/documents', json={'text': 'private-doc Kubernetes manages containers.'}, headers={'X-Request-ID': 'create_123'})
        assert created.headers['x-request-id'] == 'create_123'
        doc_id = created.json()['document_id']
        response = client.post('/ask?private-query=private-secret', json={'document_id': doc_id, 'question': 'Kubernetes manages containers'}, headers={'X-Request-ID': 'ask-123', 'Authorization': 'Bearer private-key'})
        assert response.headers['x-request-id'] == 'ask-123'
        assert response.status_code == 200
        assert client.get('/metrics').status_code == 200
    events = logs()
    llm = [e for e in events if e['event'] == 'llm_call_completed' and e['request_id'] == 'ask-123']
    assert len(llm) == 1 and llm[0]['provider'] == llm[0]['model'] == 'stub'
    assert llm[0]['outcome'] == 'success' and llm[0]['duration_ms'] >= 0
    assert not any(e['event'] == 'llm_usage_reported' for e in events)
    http = [e for e in events if e['event'] == 'http_request_completed' and e['request_id'] == 'ask-123']
    assert len(http) == 1 and http[0]['route'] == '/ask' and http[0]['status_code'] == 200
    assert all({'timestamp', 'level', 'event', 'request_id'} <= e.keys() for e in events)
    assert not any(e.get('route') in ('/metrics', '/healthz') for e in events)
    serialized = json.dumps(events)
    for secret in (doc_id, 'private-doc', 'private-query', 'private-secret', 'private-key', 'Kubernetes manages containers'):
        assert secret not in serialized


@pytest.mark.parametrize('incoming', ['x' * 65, 'bad id', 'bad/route', 'bad\"inject'])
def test_invalid_request_ids_are_replaced(incoming, logs):
    with TestClient(app) as client:
        response = client.get('/documents/no-such-document', headers={'X-Request-ID': incoming})
    value = response.headers['x-request-id']
    assert value != incoming and re.fullmatch(r'[0-9a-f]{32}', value)
    assert logs()[-1]['request_id'] == value


def test_errors_are_safe(logs):
    @app.get('/logging-test/{item_id}')
    def fail(item_id: str):
        raise RuntimeError('private-exception')
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get('/documents/private-missing').status_code == 404
        assert client.post('/documents', json={'text': 123, 'private': 'private-body'}).status_code == 422
        response = client.get('/logging-test/private-path?secret=private-query', headers={'X-Request-ID': 'error-id'})
        assert response.status_code == 500 and response.text == 'Internal Server Error'
        assert response.headers['x-request-id'] == 'error-id'
    events = logs()
    assert any(e['event'] == 'http_request_failed' and e['reason'] == 'unexpected_error' for e in events)
    assert any(e.get('route') == '/logging-test/{item_id}' and e.get('status_code') == 500 for e in events)
    for secret in ('private-missing', 'private-body', 'private-path', 'private-query', 'private-exception'):
        assert secret not in json.dumps(events)


def test_openrouter_usage_and_correlation(logs):
    def handler(request):
        return httpx.Response(200, json={'usage': {'prompt_tokens': 7, 'completion_tokens': 2}, 'choices': [{'message': {'content': 'private-answer'}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as provider:
        app.dependency_overrides[get_llm] = lambda: OpenRouterLLM('private-key', model='test/model', client=provider)
        try:
            with TestClient(app) as client:
                doc = client.post('/documents', json={'text': 'private-excerpt Kubernetes manages containers.'}).json()['document_id']
                response = client.post('/ask', headers={'X-Request-ID': 'provider-request'}, json={'document_id': doc, 'question': 'Kubernetes manages containers'})
                assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()
    events = [e for e in logs() if e['request_id'] == 'provider-request']
    usage = next(e for e in events if e['event'] == 'llm_usage_reported')
    assert (usage['provider'], usage['model'], usage['input_tokens'], usage['output_tokens']) == ('openrouter', 'test/model', 7, 2)
    assert {e['event'] for e in events} >= {'llm_call_completed', 'http_request_completed'}
    assert all(secret not in json.dumps(events) for secret in ('private-key', 'private-excerpt', 'private-answer', 'Kubernetes manages containers', doc))


@pytest.mark.parametrize(('kind', 'outcome', 'reason'), [('timeout', 'timeout', 'timeout'), ('rate', 'rate_limited', 'rate_limited'), ('provider', 'error', 'provider_error'), ('http', 'error', 'error')])
def test_provider_failure_logs_are_sanitized(kind, outcome, reason, logs):
    def handler(request):
        if kind == 'timeout':
            raise httpx.ReadTimeout('private-error', request=request)
        if kind == 'rate':
            return httpx.Response(429, text='private-error')
        if kind == 'http':
            return httpx.Response(500, text='private-error')
        return httpx.Response(200, json={'error': {'message': 'private-error'}})
    token = request_id_context.set('failure-id')
    try:
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(LLMProviderError):
                OpenRouterLLM('private-key', client=client).generate('private-question', ['private-context'])
    finally:
        request_id_context.reset(token)
    event = next(e for e in logs() if e['event'] == 'llm_call_completed')
    assert (event['request_id'], event['outcome'], event['reason']) == ('failure-id', outcome, reason)
    assert all(secret not in json.dumps(logs()) for secret in ('private-error', 'private-key', 'private-question', 'private-context'))


def test_concurrent_and_sequential_context_isolation(logs):
    def call(i):
        with TestClient(app) as client:
            return client.get('/documents/missing', headers={'X-Request-ID': f'req_{i}'}).headers['x-request-id']
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(call, range(16))) == [f'req_{i}' for i in range(16)]
    call(20)
    ids = [e['request_id'] for e in logs() if e['event'] == 'http_request_completed']
    assert sorted(ids) == sorted([f'req_{i}' for i in range(16)] + ['req_20'])
    assert request_id_context.get() is None


def test_logger_configuration_is_idempotent():
    before = list(logger.handlers)
    assert configure_logger() is logger
    assert logger.handlers == before


def test_concurrent_llm_calls_keep_request_context(logs):
    with TestClient(app) as client:
        document = client.post('/documents', json={'text': 'Kubernetes manages containers.'}).json()['document_id']
        def ask(i):
            return client.post('/ask', headers={'X-Request-ID': f'llm_{i}'}, json={'document_id': document, 'question': 'Kubernetes manages containers'}).status_code
        with ThreadPoolExecutor(max_workers=6) as pool:
            assert list(pool.map(ask, range(12))) == [200] * 12
    calls = [e['request_id'] for e in logs() if e['event'] == 'llm_call_completed']
    assert sorted(calls) == sorted(f'llm_{i}' for i in range(12))


def test_usage_logs_only_valid_reported_values(logs):
    def handler(request):
        return httpx.Response(200, json={'usage': {'prompt_tokens': True, 'completion_tokens': 5}, 'choices': [{'message': {'content': 'answer'}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        OpenRouterLLM('test-key', client=client).generate('question', ['context'])
    usage = next(e for e in logs() if e['event'] == 'llm_usage_reported')
    assert usage['output_tokens'] == 5 and 'input_tokens' not in usage
