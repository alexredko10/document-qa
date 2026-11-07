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