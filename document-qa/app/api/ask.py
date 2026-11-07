"""POST /ask: question answering within a session."""

import time
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.deps import ServicesDep
from app.models import AskRequest, AskResponse, SourceOut
from app.store.base import DocumentStatus, Role

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest, svc: ServicesDep) -> AskResponse:
    started = time.perf_counter()
    store = svc.store

    size = len(payload.question.encode("utf-8"))
    if size > svc.settings.max_question_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Question is {size} bytes; the limit is {svc.settings.max_question_bytes}.",
        )

    if payload.session_id is not None:
        session = await store.get_session(str(payload.session_id))
        if session is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Session not found.")
    else:
        session = await store.create_session()

    document_ids: list[str] | None = None
    if payload.document_ids is not None:
        document_ids = [str(d) for d in payload.document_ids]
        for doc_id in document_ids:
            doc = await store.get_document(doc_id)
            if doc is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, detail=f"Document {doc_id} not found."
                )
            if doc.status is not DocumentStatus.APPROVED:
                raise HTTPException(
                    status.HTTP_409_CONFLICT, detail=f"Document {doc_id} is not approved yet."
                )

    history = await store.recent_messages(session.id, svc.settings.history_messages)
    result = await svc.pipeline.answer(payload.question, history, document_ids)

    sources = [SourceOut.of(c) for c in result.sources]
    await store.add_message(session.id, Role.USER, payload.question)
    await store.add_message(
        session.id,
        Role.ASSISTANT,
        result.answer,
        sources=[s.model_dump(mode="json", exclude={"text"}) for s in sources],
        model_id=result.model_id,
        prompt_version=result.prompt_version,
    )

    return AskResponse(
        session_id=UUID(session.id),
        answer=result.answer,
        grounded=result.grounded,
        sources=sources,
        model_id=result.model_id,
        prompt_version=result.prompt_version,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
