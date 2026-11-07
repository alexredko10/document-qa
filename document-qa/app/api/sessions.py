"""Session lifecycle: create a session, read its history."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import ServicesDep
from app.models import MessageOut, SessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(svc: ServicesDep) -> SessionOut:
    return SessionOut.of(await svc.store.create_session())


@router.get("/{session_id}/messages", response_model=list[MessageOut])
async def session_messages(
    session_id: UUID, svc: ServicesDep, limit: int = Query(default=50, ge=1, le=500)
) -> list[MessageOut]:
    sid = str(session_id)
    if await svc.store.get_session(sid) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return [MessageOut.of(m) for m in await svc.store.recent_messages(sid, limit)]
