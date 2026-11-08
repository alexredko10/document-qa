"""Low-cardinality instrumentation for provider calls."""
from functools import wraps
from time import perf_counter

from prometheus_client import Counter, Histogram
from opentelemetry.trace import Status, StatusCode

from app.observability import tracing
from app.observability.logging import log_event, model_id
from app.llm.metadata import update_metadata

LLM_CALLS = Counter("llm_calls_total", "LLM calls by provider and outcome", ["provider", "outcome"])
LLM_DURATION = Histogram(
    "llm_call_duration_seconds",
    "LLM call duration including failures",
    ["provider"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 20.0, 30.0),
)
LLM_TOKENS = Counter("llm_tokens_total", "Provider-reported tokens", ["provider", "direction"])


def instrument_llm(provider, *, require_context=True):
    def decorate(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            # An empty context is handled locally and makes no provider call.
            context = kwargs.get("context", args[2] if len(args) > 2 else None)
            if require_context and not context:
                return func(*args, **kwargs)
            start = perf_counter()
            outcome = "success"
            reason = None
            model = model_id(provider, args[0])
            update_metadata(invoked=True, provider=provider,
                            requested_model=getattr(args[0], "model", None) if provider == "openrouter" else None,
                            actual_model="stub" if provider == "stub" else None)
            try:
                if provider == "openrouter":
                    with tracing.get_tracer().start_as_current_span(
                        "llm.generation",
                        attributes={"llm.provider": provider},
                        record_exception=False,
                        set_status_on_exception=False,
                    ) as span:
                        try:
                            return func(*args, **kwargs)
                        except Exception:
                            span.set_status(Status(StatusCode.ERROR))
                            raise
                return func(*args, **kwargs)
            except Exception as exc:
                raw_reason = getattr(exc, "reason", "")
                outcome = raw_reason if raw_reason in {"timeout", "rate_limited"} else "error"
                reason = raw_reason if raw_reason in {"timeout", "rate_limited", "connection_error", "provider_error", "invalid_response", "empty_response"} else "error"
                raise
            finally:
                LLM_CALLS.labels(provider, outcome).inc()
                elapsed = perf_counter() - start
                LLM_DURATION.labels(provider).observe(elapsed)
                update_metadata(duration_ms=round(elapsed * 1000, 3))
                fields = {"provider": provider, "model": model, "outcome": outcome, "duration_ms": round(elapsed * 1000, 3)}
                if reason is not None:
                    fields["reason"] = reason
                log_event("llm_call_completed", **fields)
        return wrapped
    return decorate


def record_usage(provider, usage, model="unknown"):
    if not isinstance(usage, dict):
        return
    valid = {}
    for field, direction in (("prompt_tokens", "input"), ("completion_tokens", "output")):
        value = usage.get(field)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            LLM_TOKENS.labels(provider, direction).inc(value)
            valid[f"{direction}_tokens"] = value
    if valid:
        log_event("llm_usage_reported", provider=provider, model=model, **valid)
