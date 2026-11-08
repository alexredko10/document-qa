"""Small, opt-in OpenTelemetry setup for the application."""
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.observability.logging import log_event

SERVICE_NAME = "document-qa"
_provider: TracerProvider | None = None


def configure_tracing() -> bool:
    global _provider
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "").strip()
    if not endpoint:
        return False
    if _provider is not None:
        return True

    try:
        provider = TracerProvider(resource=Resource.create({"service.name": SERVICE_NAME}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
        _provider = provider
    except Exception:
        # A bad endpoint or exporter setup must not prevent the API from starting.
        log_event("tracing_setup_failed", provider="tempo", reason="configuration_error")
        return False
    return True


def get_tracer():
    return trace.get_tracer(SERVICE_NAME)
