"""In-memory store for local runs and tests (single replica only)."""

import uuid
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import numpy as np

from app.rag.retriever import cosine_scores
from app.store.base import (
    ChunkInput,
    Document,
    DocumentStatus,
    DocumentStore,
    Message,
    Role,
    ScoredChunk,
    Session,
)


class InMemoryStore(DocumentStore):
    """Process-local state. Data is lost on restart and not shared between replicas,
    which is why the prod values use STORE_BACKEND=postgres."""

    def __init__(self) -> None:
        self._docs: dict[str, Document] = {}
        self._chunks: dict[str, list[ChunkInput]] = {}
        self._sessions: dict[str, Session] = {}
        self._messages: dict[str, list[Message]] = {}

    async def ping(self) -> None:
        return None

    async def create_document(
        self,
        *,
        title: str | None,
        size_bytes: int,
        status: DocumentStatus,
        chunks: Sequence[ChunkInput],
    ) -> Document:
        now = datetime.now(UTC)
        doc = Document(
            id=str(uuid.uuid4()),
            title=title,
            status=status,
            size_bytes=size_bytes,
            chunk_count=len(chunks),
            created_at=now,
            approved_at=now if status is DocumentStatus.APPROVED else None,
        )
        self._docs[doc.id] = doc
        self._chunks[doc.id] = list(chunks)
        return doc

    async def get_document(self, document_id: str) -> Document | None:
        return self._docs.get(document_id)

    async def list_documents(
        self, status: DocumentStatus | None = None, limit: int = 100
    ) -> list[Document]:
        docs = sorted(self._docs.values(), key=lambda d: d.created_at, reverse=True)
        return [d for d in docs if status is None or d.status is status][:limit]

    async def set_status(self, document_id: str, status: DocumentStatus) -> Document | None:
        doc = self._docs.get(document_id)
        if doc is None:
            return None
        if doc.status is not status:
            approved_at = datetime.now(UTC) if status is DocumentStatus.APPROVED else None
            doc = replace(doc, status=status, approved_at=approved_at)
            self._docs[document_id] = doc
        return doc

    async def search(
        self,
        embedding: Sequence[float],
        top_k: int,
        document_ids: Sequence[str] | None = None,
    ) -> list[ScoredChunk]:
        allowed = set(document_ids) if document_ids is not None else None
        candidates: list[tuple[str, ChunkInput]] = [
            (doc_id, chunk)
            for doc_id, doc in self._docs.items()
            if doc.status is DocumentStatus.APPROVED and (allowed is None or doc_id in allowed)
            for chunk in self._chunks[doc_id]
        ]
        if not candidates:
            return []
        matrix = np.asarray([c.embedding for _, c in candidates], dtype=np.float32)
        scores = cosine_scores(embedding, matrix)
        order = np.argsort(-scores)[:top_k]
        return [
            ScoredChunk(
                document_id=candidates[i][0],
                index=candidates[i][1].index,
                text=candidates[i][1].text,
                score=float(scores[i]),
            )
            for i in order
        ]

    async def get_chunk(self, document_id: str, index: int) -> ScoredChunk | None:
        doc = self._docs.get(document_id)
        if doc is None or doc.status is not DocumentStatus.APPROVED:
            return None
        for chunk in self._chunks[document_id]:
            if chunk.index == index:
                return ScoredChunk(document_id=document_id, index=index, text=chunk.text, score=1.0)
        return None

    async def create_session(self) -> Session:
        session = Session(id=str(uuid.uuid4()), created_at=datetime.now(UTC))
        self._sessions[session.id] = session
        self._messages[session.id] = []
        return session

    async def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def add_message(
        self,
        session_id: str,
        role: Role,
        content: str,
        *,
        sources: list[dict[str, Any]] | None = None,
        model_id: str | None = None,
        prompt_version: str | None = None,
    ) -> None:
        self._messages[session_id].append(
            Message(
                role=role,
                content=content,
                created_at=datetime.now(UTC),
                sources=sources or [],
                model_id=model_id,
                prompt_version=prompt_version,
            )
        )

    async def recent_messages(self, session_id: str, limit: int) -> list[Message]:
        if limit <= 0:
            return []
        return self._messages.get(session_id, [])[-limit:]
