"""Per-call metadata, scoped to the synchronous request handler."""
from contextvars import ContextVar

metadata_context: ContextVar[dict | None] = ContextVar("llm_metadata", default=None)


def update_metadata(**fields):
    current = metadata_context.get()
    if current is not None:
        current.update(fields)
