"""Postgres + pgvector store (production backend)."""

import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import psycopg
from pgvector.psycopg import register_vector_async
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

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

# Arbitrary constant shared by every replica: only one applies migrations at a time.
_MIGRATION_LOCK_ID = 7_413_001

_DOC_COLUMNS = "id::text AS id, title, status, size_bytes, chunk_count, created_at, approved_at"


async def run_migrations(dsn: str, directory: Path) -> list[str]:
    """Apply pending *.sql files in lexical order. Returns the versions applied."""
    applied_now: list[str] = []
    async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
        await conn.execute("SELECT pg_advisory_lock(%s)", (_MIGRATION_LOCK_ID,))
        try:
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " version text PRIMARY KEY,"
                " applied_at timestamptz NOT NULL DEFAULT now())"
            )
            cur = await conn.execute("SELECT version FROM schema_migrations")
            done = {row[0] for row in await cur.fetchall()}
            for path in sorted(directory.glob("*.sql")):
                if path.name in done:
                    continue
                async with conn.transaction():
                    await conn.execute(path.read_text())
                    await conn.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,)
                    )
                applied_now.append(path.name)
        finally:
            await conn.execute("SELECT pg_advisory_unlock(%s)", (_MIGRATION_LOCK_ID,))
    return applied_now


def _to_document(row: dict[str, Any]) -> Document:
    return Document(
        id=row["id"],
        title=row["title"],
        status=DocumentStatus(row["status"]),
        size_bytes=row["size_bytes"],
        chunk_count=row["chunk_count"],
        created_at=row["created_at"],
        approved_at=row["approved_at"],
    )


class PostgresStore(DocumentStore):
    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 10) -> None:
        self._pool = AsyncConnectionPool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            open=False,
            kwargs={"row_factory": dict_row},
            configure=register_vector_async,
        )

    async def open(self) -> None:
        await self._pool.open(wait=True, timeout=15)

    async def close(self) -> None:
        await self._pool.close()

    async def ping(self) -> None:
        async with self._pool.connection() as conn:
            await conn.execute("SELECT 1")

    # --- documents ---
    async def create_document(
        self,
        *,
        title: str | None,
        size_bytes: int,
        status: DocumentStatus,
        chunks: Sequence[ChunkInput],
    ) -> Document:
        doc_id = str(uuid.uuid4())
        async with self._pool.connection() as conn, conn.transaction():
            cur = await conn.execute(
                f"""
                INSERT INTO documents (id, title, status, size_bytes, chunk_count, approved_at)
                VALUES (%s, %s, %s, %s, %s,
                        CASE WHEN %s = 'approved' THEN now() END)
                RETURNING {_DOC_COLUMNS}
                """,
                (doc_id, title, status.value, size_bytes, len(chunks), status.value),
            )
            row = await cur.fetchone()
            async with conn.cursor() as c:
                await c.executemany(
                    "INSERT INTO chunks (document_id, chunk_index, text, embedding)"
                    " VALUES (%s, %s, %s, %s)",
                    [
                        (doc_id, ch.index, ch.text, np.asarray(ch.embedding, dtype=np.float32))
                        for ch in chunks
                    ],
                )
        assert row is not None
        return _to_document(row)

    async def get_document(self, document_id: str) -> Document | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                f"SELECT {_DOC_COLUMNS} FROM documents WHERE id = %s", (document_id,)
            )
            row = await cur.fetchone()
        return _to_document(row) if row else None

    async def list_documents(
        self, status: DocumentStatus | None = None, limit: int = 100
    ) -> list[Document]:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                f"""
                SELECT {_DOC_COLUMNS} FROM documents
                WHERE %(status)s::text IS NULL OR status = %(status)s
                ORDER BY created_at DESC LIMIT %(limit)s
                """,
                {"status": status.value if status else None, "limit": limit},
            )
            rows = await cur.fetchall()
        return [_to_document(r) for r in rows]

    async def set_status(self, document_id: str, status: DocumentStatus) -> Document | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                f"""
                UPDATE documents
                SET status = %(status)s,
                    approved_at = CASE
                        WHEN %(status)s = 'approved' THEN COALESCE(approved_at, now())
                    END
                WHERE id = %(id)s
                RETURNING {_DOC_COLUMNS}
                """,
                {"id": document_id, "status": status.value},
            )
            row = await cur.fetchone()
        return _to_document(row) if row else None

    # --- retrieval ---
    async def search(
        self,
        embedding: Sequence[float],
        top_k: int,
        document_ids: Sequence[str] | None = None,
    ) -> list[ScoredChunk]:
        query = np.asarray(embedding, dtype=np.float32)
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT c.document_id::text AS document_id, c.chunk_index, c.text,
                       1 - (c.embedding <=> %(q)s) AS score
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE d.status = 'approved'
                  AND (%(ids)s::uuid[] IS NULL OR c.document_id = ANY(%(ids)s::uuid[]))
                ORDER BY c.embedding <=> %(q)s
                LIMIT %(k)s
                """,
                {
                    "q": query,
                    "ids": list(document_ids) if document_ids is not None else None,
                    "k": top_k,
                },
            )
            rows = await cur.fetchall()
        return [
            ScoredChunk(
                document_id=r["document_id"],
                index=r["chunk_index"],
                text=r["text"],
                score=float(r["score"]),
            )
            for r in rows
        ]

    async def get_chunk(self, document_id: str, index: int) -> ScoredChunk | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT c.text FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.document_id = %s AND c.chunk_index = %s AND d.status = 'approved'
                """,
                (document_id, index),
            )
            row = await cur.fetchone()
        if row is None:
            return None
        return ScoredChunk(document_id=document_id, index=index, text=row["text"], score=1.0)

    # --- conversation context ---
    async def create_session(self) -> Session:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "INSERT INTO sessions (id) VALUES (%s) RETURNING id::text AS id, created_at",
                (str(uuid.uuid4()),),
            )
            row = await cur.fetchone()
        assert row is not None
        return Session(id=row["id"], created_at=row["created_at"])

    async def get_session(self, session_id: str) -> Session | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT id::text AS id, created_at FROM sessions WHERE id = %s", (session_id,)
            )
            row = await cur.fetchone()
        return Session(id=row["id"], created_at=row["created_at"]) if row else None

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
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO messages (session_id, role, content, sources, model_id, prompt_version)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (session_id, role.value, content, Jsonb(sources or []), model_id, prompt_version),
            )

    async def recent_messages(self, session_id: str, limit: int) -> list[Message]:
        if limit <= 0:
            return []
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT role, content, created_at, sources, model_id, prompt_version FROM (
                    SELECT * FROM messages WHERE session_id = %s ORDER BY id DESC LIMIT %s
                ) recent ORDER BY id
                """,
                (session_id, limit),
            )
            rows = await cur.fetchall()
        return [
            Message(
                role=Role(r["role"]),
                content=r["content"],
                created_at=r["created_at"],
                sources=r["sources"],
                model_id=r["model_id"],
                prompt_version=r["prompt_version"],
            )
            for r in rows
        ]
