import json
from pathlib import Path

import httpx
import pytest
from prometheus_client import REGISTRY

from app.llm.openrouter import LLMProviderError, OpenRouterLLM
from app.llm.stub import StubLLM


def sample(name, labels):
    return REGISTRY.get_sample_value(name, labels) or 0


def test_stub_and_provider_usage():
    labels = {'provider': 'stub', 'outcome': 'success'}
    before = sample('llm_calls_total', labels)
    assert StubLLM().generate('private question', ['private context']) == 'private context'
    assert sample('llm_calls_total', labels) == before + 1
    token_labels = {'provider': 'openrouter', 'direction': 'input'}
    before = sample('llm_tokens_total', token_labels)
    def handler(request):
        return httpx.Response(200, json={'usage': {'prompt_tokens': 12, 'completion_tokens': 3}, 'choices': [{'message': {'content': 'answer'}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        OpenRouterLLM('secret-key', client=client).generate('question', ['context'])
    assert sample('llm_tokens_total', token_labels) == before + 12


@pytest.mark.parametrize(('response', 'outcome'), [(429, 'rate_limited'), (500, 'error'), ('timeout', 'timeout')])
def test_provider_failures_are_timed(response, outcome):
    labels = {'provider': 'openrouter', 'outcome': outcome}
    before = sample('llm_calls_total', labels)
    duration = sample('llm_call_duration_seconds_count', {'provider': 'openrouter'})
    def handler(request):
        if response == 'timeout':
            raise httpx.ReadTimeout('secret-key', request=request)
        return httpx.Response(response)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LLMProviderError):
            OpenRouterLLM('secret-key', client=client).generate('question', ['context'])
    assert sample('llm_calls_total', labels) == before + 1
    assert sample('llm_call_duration_seconds_count', {'provider': 'openrouter'}) == duration + 1


def test_dashboard_metrics_and_provisioning():
    root = Path(__file__).resolve().parents[2]
    dashboard = json.loads((root / 'document-qa/deploy/grafana/document-qa.json').read_text())
    assert dashboard['title'] == 'Document QA — Service Overview'
    expressions = ' '.join(t['expr'] for p in dashboard['panels'] for t in p['targets'])
    for name in ('up', 'http_requests_total', 'http_request_duration_seconds_bucket', 'http_requests_in_flight', 'llm_calls_total', 'llm_call_duration_seconds_bucket', 'llm_tokens_total'):
        assert name in expressions
    assert all(p['datasource']['uid'] == 'prometheus' for p in dashboard['panels'])
    for p in dashboard['panels']:
        for target in p['targets']:
            if 'http_requests_total' in target['expr'] or 'http_request_duration_seconds_bucket' in target['expr']:
                assert 'route!~"/healthz|/metrics"' in target['expr']


def test_missing_usage_does_not_invent_tokens_or_leak_labels():
    from prometheus_client import generate_latest

    labels = {'provider': 'openrouter', 'direction': 'input'}
    before = sample('llm_tokens_total', labels)
    def handler(request):
        return httpx.Response(200, json={'choices': [{'message': {'content': 'private-answer'}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        OpenRouterLLM('private-api-key', client=client).generate('private-question', ['private-excerpt'])
    assert sample('llm_tokens_total', labels) == before
    output = generate_latest().decode()
    assert all(secret not in output for secret in ('private-api-key', 'private-question', 'private-excerpt', 'private-answer'))


def test_openrouter_histogram_has_30_second_bucket():
    labels = {'provider': 'openrouter', 'le': '30.0'}
    before = sample('llm_call_duration_seconds_bucket', labels)
    def handler(request):
        return httpx.Response(200, json={'choices': [{'message': {'content': 'answer'}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        OpenRouterLLM('test-key', client=client).generate('question', ['context'])
    assert REGISTRY.get_sample_value('llm_call_duration_seconds_bucket', labels) == before + 1


def test_provider_reported_usage_counted_on_error():
    from prometheus_client import generate_latest

    input_labels = {'provider': 'openrouter', 'direction': 'input'}
    output_labels = {'provider': 'openrouter', 'direction': 'output'}
    failure_labels = {'provider': 'openrouter', 'outcome': 'error'}
    before_input = sample('llm_tokens_total', input_labels)
    before_output = sample('llm_tokens_total', output_labels)
    before_failure = sample('llm_calls_total', failure_labels)
    def handler(request):
        return httpx.Response(200, json={'usage': {'prompt_tokens': 7, 'completion_tokens': 2}, 'error': {'message': 'provider failed private secret'}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LLMProviderError) as exc:
            OpenRouterLLM('test-key', client=client).generate('question', ['context'])
    assert exc.value.reason == 'provider_error'
    assert sample('llm_tokens_total', input_labels) == before_input + 7
    assert sample('llm_tokens_total', output_labels) == before_output + 2
    assert sample('llm_calls_total', failure_labels) == before_failure + 1
    assert 'provider failed private secret' not in generate_latest().decode()


@pytest.mark.parametrize('body', [[], 'unexpected', None, 42])
def test_non_object_response_is_invalid(body):
    def handler(request):
        # httpx treats json=None as no body, so encode JSON explicitly.
        return httpx.Response(200, content=json.dumps(body), headers={'Content-Type': 'application/json'})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LLMProviderError) as exc:
            OpenRouterLLM('test-key', client=client).generate('question', ['context'])
    assert exc.value.reason == 'invalid_response'


@pytest.mark.parametrize('usage', [None, {'prompt_tokens': -1, 'completion_tokens': -2}, {'prompt_tokens': True, 'completion_tokens': False}, {'prompt_tokens': 1.5, 'completion_tokens': '2'}])
def test_invalid_or_missing_usage_not_counted(usage):
    input_labels = {'provider': 'openrouter', 'direction': 'input'}
    output_labels = {'provider': 'openrouter', 'direction': 'output'}
    before_input = sample('llm_tokens_total', input_labels)
    before_output = sample('llm_tokens_total', output_labels)
    def handler(request):
        body = {'choices': [{'message': {'content': 'answer'}}]}
        if usage is not None:
            body['usage'] = usage
        return httpx.Response(200, json=body)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        OpenRouterLLM('test-key', client=client).generate('question', ['context'])
    assert sample('llm_tokens_total', input_labels) == before_input
    assert sample('llm_tokens_total', output_labels) == before_output


def test_usage_counted_before_answer_validation():
    labels = {'provider': 'openrouter', 'direction': 'input'}
    before = sample('llm_tokens_total', labels)
    def handler(request):
        return httpx.Response(200, json={'usage': {'prompt_tokens': 4}, 'choices': []})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LLMProviderError) as exc:
            OpenRouterLLM('test-key', client=client).generate('question', ['context'])
    assert exc.value.reason == 'invalid_response'
    assert sample('llm_tokens_total', labels) == before + 4
