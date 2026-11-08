import io
import json
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient

from app.llm.openrouter import OpenRouterLLM
from app.llm.provider import get_llm
from app.main import app
from app.observability.logging import logger


def upload(client):
    response = client.post('/documents', json={'text': 'Kubernetes manages containers and provides a platform.'})
    assert response.status_code == 201
    return response.json()['document_id']


def ask(client, document_id, question='Kubernetes manages containers'):
    return client.post('/ask', json={'document_id': document_id, 'question': question})


def test_demo_assets_and_stub_response():
    with TestClient(app) as client:
        page = client.get('/demo')
        assert page.status_code == 200 and 'Document QA' in page.text
        assert client.get('/demo/console.css').status_code == 200
        assert client.get('/demo/console.js').status_code == 200
        assert client.get('/demo/unknown').status_code == 404
        response = ask(client, upload(client))
    assert response.status_code == 200
    data = response.json()
    assert data['answer'] and data['source_chunks']
    assert data['llm']['invoked'] is True and data['llm']['provider'] == 'stub'
    assert data['llm']['actual_model'] == 'stub' and data['llm']['requested_model'] is None
    assert data['llm']['duration_ms'] >= 0
    assert all(data['llm'][field] is None for field in ('input_tokens', 'output_tokens', 'cost_usd'))


def test_locally_answered_request_has_no_fake_metadata():
    with TestClient(app) as client:
        response = ask(client, upload(client), 'How many moons does Jupiter have?')
    metadata = response.json()['llm']
    assert metadata['invoked'] is False
    assert all(value is None for key, value in metadata.items() if key != 'invoked')


@pytest.mark.parametrize('usage', [{'prompt_tokens': 7, 'completion_tokens': 2, 'cost': 0.001}, None, {'prompt_tokens': True, 'completion_tokens': -1, 'cost': True}])
def test_openrouter_metadata_and_privacy(usage):
    def handler(request):
        body = {'model': 'real/provider-model', 'choices': [{'message': {'content': 'private-answer'}}]}
        if usage is not None:
            body['usage'] = usage
        return httpx.Response(200, json=body)
    stream = io.StringIO()
    log_handler = next(h for h in logger.handlers if getattr(h, '_document_qa_handler', False))
    original = log_handler.stream
    log_handler.setStream(stream)
    try:
        with httpx.Client(transport=httpx.MockTransport(handler)) as provider:
            app.dependency_overrides[get_llm] = lambda: OpenRouterLLM('private-secret-key', model='openrouter/free', client=provider)
            try:
                with TestClient(app) as client:
                    document_id = upload(client)
                    response = ask(client, document_id)
            finally:
                app.dependency_overrides.clear()
    finally:
        log_handler.setStream(original)
    data = response.json()
    assert data['answer'] == 'private-answer'
    metadata = data['llm']
    assert metadata['provider'] == 'openrouter' and metadata['requested_model'] == 'openrouter/free'
    assert metadata['actual_model'] == 'real/provider-model' and metadata['duration_ms'] >= 0
    if usage and usage.get('prompt_tokens') == 7:
        assert (metadata['input_tokens'], metadata['output_tokens'], metadata['cost_usd']) == (7, 2, .001)
    else:
        assert all(metadata[key] is None for key in ('input_tokens', 'output_tokens', 'cost_usd'))
    for secret in ('private-answer', 'private-secret-key', 'Kubernetes manages containers', document_id):
        assert secret not in stream.getvalue()


def test_concurrent_requests_keep_metadata_separate():
    def handler(request):
        question = json.loads(request.content)['messages'][1]['content']
        n = int(question.rsplit('marker', 1)[1])
        return httpx.Response(200, json={'model': f'provider/model-{n}', 'usage': {'prompt_tokens': n}, 'choices': [{'message': {'content': f'answer-{n}'}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as provider:
        app.dependency_overrides[get_llm] = lambda: OpenRouterLLM('test-key', client=provider)
        try:
            with TestClient(app) as client:
                document_id = upload(client)
                def run(n):
                    return ask(client, document_id, f'Kubernetes manages containers marker{n}').json()
                with ThreadPoolExecutor(max_workers=8) as pool:
                    responses = list(pool.map(run, range(1, 13)))
        finally:
            app.dependency_overrides.clear()
    for n, data in enumerate(responses, 1):
        assert data['answer'] == f'answer-{n}'
        assert data['llm']['actual_model'] == f'provider/model-{n}'
        assert data['llm']['input_tokens'] == n
        assert data['llm']['output_tokens'] is None


def test_router_identifier_is_not_claimed_as_actual_model():
    def handler(request):
        return httpx.Response(200, json={'model': 'openrouter/free', 'choices': [{'message': {'content': 'answer'}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as provider:
        app.dependency_overrides[get_llm] = lambda: OpenRouterLLM('test-key', client=provider)
        try:
            with TestClient(app) as client:
                result = ask(client, upload(client)).json()
        finally:
            app.dependency_overrides.clear()
    assert result['llm']['requested_model'] == 'openrouter/free'
    assert result['llm']['actual_model'] is None
