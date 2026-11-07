"""Pydantic request/response schemas shared by the API layer.

Size limits are enforced in bytes (MAX_DOCUMENT_BYTES / MAX_QUESTION_BYTES) by the
handlers and the body-size middleware so oversized input gets 413, not a 422
validation error.
"""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from app.store.base import Document, DocumentStatus, Message, Role, ScoredChunk, Session

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DocumentCreate(BaseModel):
    text: str = Field(min_length=1, description="Plain UTF-8 text, at most MAX_DOCUMENT_BYTES.")
    title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None


class DocumentOut(BaseModel):
    id: UUID
    title: str | None
    status: DocumentStatus
    size_bytes: int
    chunk_count: int
    created_at: datetime
    approved_at: datetime | None

    @classmethod
    def of(cls, doc: Document) -> "DocumentOut":
        return cls(
            id=UUID(doc.id),
            title=doc.title,
            status=doc.status,
            size_bytes=doc.size_bytes,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at,
            approved_at=doc.approved_at,
        )


class AskRequest(BaseModel):
    question: NonBlank = Field(description="At most MAX_QUESTION_BYTES of UTF-8.")
    session_id: UUID | None = Field(
        default=None, description="Continue a conversation; omitted = start a new session."
    )
    document_ids: list[UUID] | None = Field(
        default=None,
        max_length=20,
        description="Restrict retrieval to these approved documents; omitted = whole corpus.",
    )


class SourceOut(BaseModel):
    document_id: UUID
    chunk_index: int
    text: str
    score: float

    @classmethod
    def of(cls, chunk: ScoredChunk) -> "SourceOut":
        return cls(
            document_id=UUID(chunk.document_id),
            chunk_index=chunk.index,
            text=chunk.text,
            score=round(chunk.score, 4),
        )


class AskResponse(BaseModel):
    session_id: UUID
    answer: str
    grounded: bool = Field(description="False when the service refused for lack of evidence.")
    sources: list[SourceOut]
    model_id: str | None
    prompt_version: str | None
    latency_ms: int


class SessionOut(BaseModel):
    id: UUID
    created_at: datetime

    @classmethod
    def of(cls, session: Session) -> "SessionOut":
        return cls(id=UUID(session.id), created_at=session.created_at)


class MessageOut(BaseModel):
    role: Role
    content: str
    created_at: datetime
    sources: list[dict[str, Any]]
    model_id: str | None
    prompt_version: str | None

    @classmethod
    def of(cls, m: Message) -> "MessageOut":
        return cls(
            role=m.role,
            content=m.content,
            created_at=m.created_at,
            sources=m.sources,
            model_id=m.model_id,
            prompt_version=m.prompt_version,
        )
