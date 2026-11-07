"""POST /documents, POST /documents/{id}/approve, GET /documents, GET /documents/{id}."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.deps import ServicesDep
from app.models import DocumentCreate, DocumentOut
from app.store.base import ChunkInput, DocumentStatus

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def submit_document(payload: DocumentCreate, svc: ServicesDep) -> DocumentOut:
    size = len(payload.text.encode("utf-8"))
    limit = svc.settings.max_document_bytes
    if size > limit:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Document is {size} bytes; the limit is {limit} bytes.",
        )

    pieces = svc.chunker.chunk(payload.text)
    if not pieces:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Document contains no usable text."
        )

    embeddings = await asyncio.to_thread(svc.embedder.embed, pieces)
    chunks = [
        ChunkInput(index=i, text=text, embedding=emb)
        for i, (text, emb) in enumerate(zip(pieces, embeddings, strict=True))
    ]
    initial = DocumentStatus.APPROVED if svc.settings.auto_approve else DocumentStatus.PENDING
    doc = await svc.store.create_document(
        title=payload.title, size_bytes=size, status=initial, chunks=chunks
    )
    return DocumentOut.of(doc)


@router.post("/{document_id}/approve", response_model=DocumentOut)
async def approve_document(document_id: UUID, svc: ServicesDep) -> DocumentOut:
    """Idempotent: approving an approved document returns it unchanged."""
    doc = await svc.store.set_status(str(document_id), DocumentStatus.APPROVED)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return DocumentOut.of(doc)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    svc: ServicesDep, status: DocumentStatus | None = None
) -> list[DocumentOut]:
    return [DocumentOut.of(d) for d in await svc.store.list_documents(status)]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: UUID, svc: ServicesDep) -> DocumentOut:
    doc = await svc.store.get_document(str(document_id))
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return DocumentOut.of(doc)
