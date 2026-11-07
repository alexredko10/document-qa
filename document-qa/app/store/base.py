"""DocumentStore ABC: documents, chunks, approval status, sessions, messages."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class DocumentStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class Document:
    id: str
    title: str | None
    status: DocumentStatus
    size_bytes: int
    chunk_count: int
    created_at: datetime
    approved_at: datetime | None = None


@dataclass(frozen=True)
class ChunkInput:
    index: int
    text: str
    embedding: Sequence[float]


@dataclass(frozen=True)
class ScoredChunk:
    document_id: str
    index: int
    text: str
    score: float


@dataclass(frozen=True)
class Session:
    id: str
    created_at: datetime


@dataclass(frozen=True)
class Message:
    role: Role
    content: str
    created_at: datetime
    sources: list[dict[str, Any]] = field(default_factory=list)
    model_id: str | None = None
    prompt_version: str | None = None


class DocumentStore(ABC):
    """Persistence boundary. Pods stay stateless; all state lives behind this interface."""

    async def open(self) -> None:  # noqa: B027 - optional hook
        """Acquire resources (connection pools). No-op by default."""

    async def close(self) -> None:  # noqa: B027 - optional hook
        """Release resources. No-op by default."""

    @abstractmethod
    async def ping(self) -> None:
        """Raise if the backend is not reachable (used by /readyz)."""

    # --- documents ---
    @abstractmethod
    async def create_document(
        self,
        *,
        title: str | None,
        size_bytes: int,
        status: DocumentStatus,
        chunks: Sequence[ChunkInput],
    ) -> Document: ...

    @abstractmethod
    async def get_document(self, document_id: str) -> Document | None: ...

    @abstractmethod
    async def list_documents(
        self, status: DocumentStatus | None = None, limit: int = 100
    ) -> list[Document]: ...

    @abstractmethod
    async def set_status(self, document_id: str, status: DocumentStatus) -> Document | None: ...

    # --- retrieval (approved documents only) ---
    @abstractmethod
    async def search(
        self,
        embedding: Sequence[float],
        top_k: int,
        document_ids: Sequence[str] | None = None,
    ) -> list[ScoredChunk]: ...

    @abstractmethod
    async def get_chunk(self, document_id: str, index: int) -> ScoredChunk | None: ...

    # --- conversation context ---
    @abstractmethod
    async def create_session(self) -> Session: ...

    @abstractmethod
    async def get_session(self, session_id: str) -> Session | None: ...

    @abstractmethod
    async def add_message(
        self,
        session_id: str,
        role: Role,
        content: str,
        *,
        sources: list[dict[str, Any]] | None = None,
        model_id: str | None = None,
        prompt_version: str | None = None,
    ) -> None: ...

    @abstractmethod
    async def recent_messages(self, session_id: str, limit: int) -> list[Message]:
        """Last `limit` messages in chronological order."""
