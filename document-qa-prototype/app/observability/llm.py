"""Low-cardinality instrumentation for provider calls."""
from functools import wraps
from time import perf_counter

from prometheus_client import Counter, Histogram

LLM_CALLS = Counter("llm_calls_total", "LLM calls by provider and outcome", ["provider", "outcome"])
LLM_DURATION = Histogram(
    "llm_call_duration_seconds",
    "LLM call duration including failures",
    ["provider"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 20.0, 30.0),
)
LLM_TOKENS = Counter("llm_tokens_total", "Provider-reported tokens", ["provider", "direction"])


def instrument_llm(provider):
    def decorate(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            # An empty context is handled locally and makes no provider call.
            context = kwargs.get("context", args[2] if len(args) > 2 else None)
            if not context:
                return func(*args, **kwargs)
            start = perf_counter()
            outcome = "success"
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                reason = getattr(exc, "reason", "")
                outcome = reason if reason in {"timeout", "rate_limited"} else "error"
                raise
            finally:
                LLM_CALLS.labels(provider, outcome).inc()
                LLM_DURATION.labels(provider).observe(perf_counter() - start)
        return wrapped
    return decorate


def record_usage(provider, usage):
    if not isinstance(usage, dict):
        return
    for field, direction in (("prompt_tokens", "input"), ("completion_tokens", "output")):
        value = usage.get(field)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            LLM_TOKENS.labels(provider, direction).inc(value)
