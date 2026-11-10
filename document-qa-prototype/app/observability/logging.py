import json
import logging
import os
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from uuid import uuid4
from opentelemetry import trace

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
_REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z", re.ASCII)
_MODEL_ID = re.compile(r"[A-Za-z0-9._:/-]{1,128}\Z", re.ASCII)


def request_id(value: str | None) -> str:
    return value if value and _REQUEST_ID.fullmatch(value) else uuid4().hex


def model_id(provider: str, instance: object) -> str:
    if provider == "stub":
        return "stub"
    model = getattr(instance, "model", None)
    return model if isinstance(model, str) and _MODEL_ID.fullmatch(model) else "unknown"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        span_context = trace.get_current_span().get_span_context()
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "event": record.event,
            "request_id": record.correlation_id,
        }
        payload.update(record.fields)
        payload["trace_id"] = f"{span_context.trace_id:032x}" if span_context.is_valid else None
        payload["span_id"] = f"{span_context.span_id:016x}" if span_context.is_valid else None
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def configure_logger() -> logging.Logger:
    logger = logging.getLogger("document_qa.application")
    logger.setLevel(logging.getLevelNamesMapping().get(os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
    logger.propagate = False
    if not any(getattr(handler, "_document_qa_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler._document_qa_handler = True
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger


logger = configure_logger()


def log_event(event: str, *, level: int = logging.INFO, **fields: object) -> None:
    # Correlation IDs link events; callers must exclude prompts, documents and credentials.
    logger.log(level, event, extra={"event": event, "correlation_id": request_id_context.get(), "fields": fields})
