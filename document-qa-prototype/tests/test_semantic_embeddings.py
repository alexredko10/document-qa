import io
import json
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app import main
from app.observability.logging import logger
from app.rag.embedding_provider import EmbeddingError, HashEmbeddings, OpenRouterEmbeddings
from app.rag.retriever import search_vectors

MODEL = 'openai/text-embedding-3-small'


def response(vectors, **extra):
    return {'model': MODEL, 'data': [{'index': i, 'embedding': vector} for i, vector in enumerate(vectors)], **extra}


def test_hash_baseline_and_semantic_ranking():
    provider = HashEmbeddings()
    assert provider.embed(['Cats and dogs'], 'document') == provider.embed(['Cats and dogs'], 'query')
    result = search_vectors([1., 0.], ['far', 'near', 'opposite'], [[0., 1.], [1., 0.], [-1., 0.]], positive_only=False)
    assert [row.text for row in result] == ['near', 'far', 'opposite']


def test_batch_and_indices():
    payloads = []
    def handler(request):
        payload = json.loads(request.content); payloads.append(payload)
        n = len(payload['input'])
        body = response([[float(i + 1), 1.] for i in range(n)])
        body['data'].reverse()
        return httpx.Response(200, json=body)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        vectors = OpenRouterEmbeddings('test-key', client=client).embed([str(i) for i in range(40)], 'document')
    assert [len(p['input']) for p in payloads] == [32, 8]
    assert vectors[0] == [1, 1] and vectors[31] == [32, 1] and vectors[32] == [1, 1]
    assert all(p['model'] == MODEL for p in payloads)


@pytest.mark.parametrize('body', [
    {}, {'model': MODEL, 'data': []}, {'model': 'other', 'data': [{'index': 0, 'embedding': [1]}]},
    {'model': MODEL, 'data': [{'index': 1, 'embedding': [1]}]},
    {'model': MODEL, 'data': [{'index': True, 'embedding': [1]}]},
    {'model': MODEL, 'data': [{'index': 0, 'embedding': []}]},
    {'model': MODEL, 'data': [{'index': 0, 'embedding': [0, 0]}]},
    {'model': MODEL, 'data': [{'index': 0, 'embedding': [True]}]},
    {'model': MODEL, 'data': [{'index': 0, 'embedding': ['1']}]},
    {'model': MODEL, 'data': [{'index': 0, 'embedding': [float('nan')]}]},
])
def test_invalid_responses(body):
    def handler(request):
        return httpx.Response(200, content=json.dumps(body), headers={'Content-Type': 'application/json'})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(EmbeddingError):
            OpenRouterEmbeddings('test-key', client=client).embed(['question'], 'query')


def test_duplicate_indices_and_dimension_mismatch():
    for data in ([{'index': 0, 'embedding': [1]}, {'index': 0, 'embedding': [2]}],
                 [{'index': 0, 'embedding': [1]}, {'index': 1, 'embedding': [1, 2]}]):
        with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json={'model': MODEL, 'data': data}))) as client:
            with pytest.raises(EmbeddingError):
                OpenRouterEmbeddings('test-key', client=client).embed(['a', 'b'], 'document')


@pytest.mark.parametrize('kind', ['rate', 'timeout', 'http', 'malformed'])
def test_provider_failure_does_not_index(monkeypatch, kind):
    def handler(request):
        if kind == 'timeout':
            raise httpx.ReadTimeout('private-key', request=request)
        if kind == 'malformed':
            return httpx.Response(200, content='private-body')
        return httpx.Response(429 if kind == 'rate' else 503, text='private-body')
    before = (len(main.documents), len(main.document_chunks), len(main.document_vectors), len(main.document_embedding_config))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(main, 'get_embedding_provider', lambda: OpenRouterEmbeddings('private-key', client=client))
        with TestClient(main.app) as api:
            result = api.post('/documents', json={'text': 'private-document'})
    assert result.status_code == 503 and 'private' not in result.text
    assert before == (len(main.documents), len(main.document_chunks), len(main.document_vectors), len(main.document_embedding_config))


def test_semantic_retrieval_and_compatibility(monkeypatch):
    payloads = []
    def handler(request):
        data = json.loads(request.content); payloads.append(data)
        if len(data['input']) == 2:
            return httpx.Response(200, json=response([[1., 0.], [0., 1.]], usage={'prompt_tokens': 4}))
        return httpx.Response(200, json=response([[0., 1.]], usage={'prompt_tokens': 2}))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = OpenRouterEmbeddings('test-key', client=client)
        monkeypatch.setattr(main, 'get_embedding_provider', lambda: provider)
        monkeypatch.setattr(main, 'has_relevant_context', lambda *args: pytest.fail('semantic path used lexical gate'))
        with TestClient(main.app) as api:
            created = api.post('/documents', json={'text': '# One\nCars travel on roads.\n\n# Two\nCanines are friendly animals.'})
            assert created.status_code == 201
            doc = created.json()['document_id']
            result = api.post('/ask', json={'document_id': doc, 'question': 'puppy companion'})
            assert result.status_code == 200
            body = result.json()
            assert body['source_chunks'][0]['index'] == 1
            assert body['retrieval']['embedding_provider'] == 'openrouter' and body['retrieval']['embedding_model'] == MODEL
            assert body['llm']['provider'] == 'stub'
            provider.model = 'different/model'
            mismatch = api.post('/ask', json={'document_id': doc, 'question': 'puppy companion'})
            assert mismatch.status_code == 503 and len(payloads) == 2


def test_query_dimension_mismatch_and_no_context(monkeypatch):
    calls = []
    def handler(request):
        payload = json.loads(request.content); calls.append(payload)
        return httpx.Response(200, json=response([[1., 2.] if len(calls) == 1 else [1., 2., 3.]]))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(main, 'get_embedding_provider', lambda: OpenRouterEmbeddings('test-key', client=client))
        with TestClient(main.app) as api:
            doc = api.post('/documents', json={'text': 'A document about birds.'}).json()['document_id']
            assert api.post('/ask', json={'document_id': doc, 'question': 'birds'}).status_code == 503
            assert api.post('/ask', json={'question': 'birds', 'use_context': False}).status_code == 501
    assert len(calls) == 2


def test_embedding_events_metrics_and_concurrency(monkeypatch):
    stream = io.StringIO()
    log_handler = next(h for h in logger.handlers if getattr(h, '_document_qa_handler', False))
    previous = log_handler.stream
    log_handler.setStream(stream)
    def handler(request):
        return httpx.Response(200, json=response([[1., 0.]], usage={'prompt_tokens': 3}))
    labels = {'provider': 'openrouter', 'outcome': 'success'}
    before = REGISTRY.get_sample_value('embedding_requests_total', labels) or 0
    token_before = REGISTRY.get_sample_value('embedding_tokens_total', {'provider': 'openrouter'}) or 0
    try:
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            monkeypatch.setattr(main, 'get_embedding_provider', lambda: OpenRouterEmbeddings('private-key', client=client))
            with TestClient(main.app) as api:
                def run(i):
                    return api.post('/documents', headers={'X-Request-ID': f'emb-{i}'}, json={'text': 'private-content'})
                with ThreadPoolExecutor(max_workers=5) as pool:
                    results = list(pool.map(run, range(8)))
    finally:
        log_handler.setStream(previous)
    assert all(r.status_code == 201 for r in results)
    assert REGISTRY.get_sample_value('embedding_requests_total', labels) == before + 8
    assert REGISTRY.get_sample_value('embedding_tokens_total', {'provider': 'openrouter'}) == token_before + 24
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    finished = [e for e in events if e['event'] == 'embedding_request_completed']
    assert {e['request_id'] for e in finished} == {f'emb-{i}' for i in range(8)}
    assert all(e['provider'] == 'openrouter' and e['operation'] == 'document' and e['outcome'] == 'success' for e in finished)
    assert 'private-content' not in stream.getvalue() and 'private-key' not in stream.getvalue()


def test_batch_dimension_failure_is_accounted():
    calls = []
    def handler(request):
        calls.append(1)
        count = len(json.loads(request.content)['input'])
        vector = [1, 0] if len(calls) == 1 else [1, 0, 0]
        return httpx.Response(200, json=response([vector] * count))
    labels = {'provider': 'openrouter', 'outcome': 'error'}
    before = REGISTRY.get_sample_value('embedding_requests_total', labels) or 0
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(EmbeddingError):
            OpenRouterEmbeddings('test-key', client=client).embed(['text'] * 33, 'document')
    assert REGISTRY.get_sample_value('embedding_requests_total', labels) == before + 1


def test_invalid_usage_not_counted_and_large_vectors_remain_finite():
    labels = {'provider': 'openrouter'}
    before = REGISTRY.get_sample_value('embedding_tokens_total', labels) or 0
    with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=response([[1e308, 1e308]], usage={'prompt_tokens': True})))) as client:
        vector = OpenRouterEmbeddings('test-key', client=client).embed(['text'], 'query')[0]
    assert REGISTRY.get_sample_value('embedding_tokens_total', labels) == before
    assert search_vectors(vector, ['text'], [vector])[0].score == pytest.approx(1.0)


def test_concurrent_query_contexts_stay_isolated(monkeypatch):
    def handler(request):
        payload = json.loads(request.content)
        text = payload['input'][0]
        vector = [1., 0.] if text.startswith('alpha') else [0., 1.]
        return httpx.Response(200, json=response([vector]))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(main, 'get_embedding_provider', lambda: OpenRouterEmbeddings('test-key', client=client))
        with TestClient(main.app) as api:
            first = api.post('/documents', json={'text': 'alpha synthetic'}).json()['document_id']
            second = api.post('/documents', json={'text': 'beta synthetic'}).json()['document_id']
            def run(i):
                is_alpha = i % 2 == 0
                return api.post('/ask', headers={'X-Request-ID': f'query-{i}'}, json={'document_id': first if is_alpha else second, 'question': 'alpha query' if is_alpha else 'beta query'})
            with ThreadPoolExecutor(max_workers=6) as pool:
                responses = list(pool.map(run, range(12)))
    for i, result in enumerate(responses):
        assert result.status_code == 200 and result.headers['x-request-id'] == f'query-{i}'
        assert result.json()['source_chunks'][0]['text'] == ('alpha synthetic' if i % 2 == 0 else 'beta synthetic')
        assert result.json()['retrieval']['embedding_model'] == MODEL


@pytest.mark.parametrize(('kind', 'outcome'), [('rate', 'rate_limited'), ('timeout', 'timeout'), ('error', 'error')])
def test_failure_metrics_and_logs(kind, outcome):
    stream = io.StringIO()
    log_handler = next(h for h in logger.handlers if getattr(h, '_document_qa_handler', False))
    previous = log_handler.stream
    log_handler.setStream(stream)
    labels = {'provider': 'openrouter', 'outcome': outcome}
    before = REGISTRY.get_sample_value('embedding_requests_total', labels) or 0
    def handler(request):
        if kind == 'timeout':
            raise httpx.ReadTimeout('private-error', request=request)
        return httpx.Response(429 if kind == 'rate' else 500, text='private-error')
    try:
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(EmbeddingError):
                OpenRouterEmbeddings('private-key', client=client).embed(['private-input'], 'query')
    finally:
        log_handler.setStream(previous)
    assert REGISTRY.get_sample_value('embedding_requests_total', labels) == before + 1
    event = next(json.loads(line) for line in stream.getvalue().splitlines() if 'embedding_request_completed' in line)
    assert event['outcome'] == outcome and event['operation'] == 'query' and event['duration_ms'] >= 0
    assert all(secret not in stream.getvalue() for secret in ('private-error', 'private-key', 'private-input'))


@pytest.mark.parametrize(('count', 'expected', 'expected_calls'), [(256, 201, 8), (257, 413, 0)])
def test_semantic_chunk_limit_before_provider_call(monkeypatch, count, expected, expected_calls):
    calls = []
    def handler(request):
        payload = json.loads(request.content)
        calls.append(payload)
        return httpx.Response(200, json=response([[1., 2.]] * len(payload['input'])))
    monkeypatch.setattr(main, 'split_markdown', lambda *args, **kwargs: ['synthetic chunk'] * count)
    before = (len(main.documents), len(main.document_chunks), len(main.document_vectors), len(main.document_embedding_config))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(main, 'get_embedding_provider', lambda: OpenRouterEmbeddings('test-key', client=client))
        with TestClient(main.app) as api:
            result = api.post('/documents', json={'text': 'synthetic document'})
    assert result.status_code == expected and len(calls) == expected_calls
    if expected == 413:
        assert '256-chunk' in result.json()['detail']
        assert before == (len(main.documents), len(main.document_chunks), len(main.document_vectors), len(main.document_embedding_config))


def test_hash_does_not_have_semantic_chunk_limit(monkeypatch):
    monkeypatch.setattr(main, 'split_markdown', lambda *args, **kwargs: ['hash chunk'] * 257)
    monkeypatch.setattr(main, 'get_embedding_provider', HashEmbeddings)
    with TestClient(main.app) as api:
        result = api.post('/documents', json={'text': 'synthetic document'})
    assert result.status_code == 201
    assert len(main.document_chunks[result.json()['document_id']]) == 257


@pytest.mark.parametrize(('kind', 'reason'), [('timeout', 'timeout'), ('rate', 'rate_limited'), ('invalid', 'invalid_response'), ('missing', 'configuration_error')])
def test_safe_failure_reasons_at_api_boundary(monkeypatch, kind, reason):
    stream = io.StringIO()
    log_handler = next(h for h in logger.handlers if getattr(h, '_document_qa_handler', False))
    old = log_handler.stream
    log_handler.setStream(stream)
    calls = []
    def handler(request):
        calls.append(1)
        if kind == 'timeout':
            raise httpx.ReadTimeout('private-secret', request=request)
        if kind == 'rate':
            return httpx.Response(429, text='private-response')
        return httpx.Response(200, content='private-response')
    try:
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            monkeypatch.setattr(main, 'get_embedding_provider', lambda: OpenRouterEmbeddings('' if kind == 'missing' else 'private-secret', client=client))
            with TestClient(main.app) as api:
                result = api.post('/documents', headers={'X-Request-ID': 'failure-test'}, json={'text': 'private-document'})
    finally:
        log_handler.setStream(old)
    assert result.status_code == 503
    assert 'private' not in result.text
    event = next(json.loads(line) for line in stream.getvalue().splitlines() if 'embedding_request_completed' in line)
    assert event['reason'] == reason and event['request_id'] == 'failure-test'
    assert not any(secret in stream.getvalue() for secret in ('private-secret', 'private-response', 'private-document'))
    if kind == 'missing':
        assert not calls


@pytest.mark.parametrize(('dog_vector', 'expected_success'), [([1., 0.], True), ([0., 1.], False), ([0.5, 0.5], False)])
def test_manual_semantic_smoke_test_ranking(monkeypatch, capsys, dog_vector, expected_success):
    from scripts import manual_semantic_embeddings as smoke
    monkeypatch.setenv('RUN_OPENROUTER_EMBEDDING_TEST', '1')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'private-test-key')
    class FakeProvider:
        def __init__(self, *args):
            pass
        def embed(self, texts, operation):
            return [dog_vector, [0.5, 0.5]] if operation == 'document' else [[1., 0.]]
    monkeypatch.setattr(smoke, 'OpenRouterEmbeddings', FakeProvider)
    if expected_success:
        smoke.main()
        assert 'passed' in capsys.readouterr().out
    else:
        with pytest.raises(SystemExit) as exc:
            smoke.main()
        assert 'failed' in str(exc.value)
        assert 'private-test-key' not in str(exc.value)


@pytest.mark.parametrize(('configured', 'returned', 'accepted'), [
    (MODEL, MODEL, True),
    (MODEL, 'text-embedding-3-small', True),
    (MODEL, 'text-embedding-3-large', False),
    ('another/text-embedding-3-small', 'text-embedding-3-small', False),
])
def test_openrouter_response_model_validation(configured, returned, accepted):
    def handler(request):
        return httpx.Response(200, json={'model': returned, 'data': [{'index': 0, 'embedding': [1., 0.]}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = OpenRouterEmbeddings('test-key', model=configured, client=client)
        if accepted:
            assert provider.embed(['synthetic'], 'query') == [[1., 0.]]
        else:
            with pytest.raises(EmbeddingError) as exc:
                provider.embed(['synthetic'], 'query')
            assert exc.value.reason == 'invalid_response'


def test_shortened_model_supports_document_and_question(monkeypatch):
    requests = []
    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        return httpx.Response(200, json={'model': 'text-embedding-3-small', 'data': [{'index': i, 'embedding': [1., 0.]} for i in range(len(payload['input']))]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(main, 'get_embedding_provider', lambda: OpenRouterEmbeddings('test-key', client=client))
        with TestClient(main.app) as api:
            created = api.post('/documents', json={'text': 'A synthetic document about dogs.'})
            assert created.status_code == 201
            document_id = created.json()['document_id']
            result = api.post('/ask', json={'document_id': document_id, 'question': 'puppy companion'})
    assert result.status_code == 200
    assert result.json()['source_chunks']
    assert result.json()['retrieval']['embedding_model'] == MODEL
    assert main.document_embedding_config[document_id] == ('openrouter', MODEL, 2)
    assert len(requests) == 2 and all(request['model'] == MODEL for request in requests)
