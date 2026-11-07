from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.main import app


def test_metrics_endpoint_and_http_counter():
    labels = {
        "method": "GET",
        "route": "/healthz",
        "status": "200",
    }

    before = (
        REGISTRY.get_sample_value(
            "http_requests_total",
            labels,
        ) or 0
    )

    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200

        after = REGISTRY.get_sample_value(
            "http_requests_total",
            labels,
        )

        assert after == before + 1

        metrics = client.get("/metrics")

        assert metrics.status_code == 200
        assert "http_requests_total" in metrics.text
        assert "http_request_duration_seconds_bucket" in metrics.text
        assert "http_requests_in_flight" in metrics.text

    assert REGISTRY.get_sample_value(
        "http_requests_in_flight"
    ) == 0

def test_bounded_routes_scrapes_and_exceptions():
    @app.get('/metrics-test-error/{item_id}')
    def error(item_id: str):
        raise RuntimeError('private-secret')

    labels = {'method': 'GET', 'route': '/metrics-test-error/{item_id}', 'status': '500'}
    before = REGISTRY.get_sample_value('http_requests_total', labels) or 0
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get('/metrics-test-error/private-document-id').status_code == 500
        client.request('UNUSUAL-secret', '/unknown-private-document-id')
        body = client.get('/metrics').text
        client.get('/metrics')
    assert REGISTRY.get_sample_value('http_requests_total', labels) == before + 1
    assert REGISTRY.get_sample_value('http_request_duration_seconds_count', {'method': 'GET', 'route': '/metrics-test-error/{item_id}'}) >= 1
    assert REGISTRY.get_sample_value('http_requests_in_flight') == 0
    assert all(value not in body for value in ('private-document-id', 'private-secret', 'UNUSUAL-secret', 'route="/metrics"'))
