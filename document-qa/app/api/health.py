"""Liveness/readiness probes: /healthz, /readyz."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.deps import ServicesDep

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness: the process is serving. Never checks dependencies, so a database
    outage does not make Kubernetes restart every pod."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(svc: ServicesDep) -> JSONResponse:
    """Readiness: the store is reachable; otherwise the pod is taken out of the Service."""
    try:
        await svc.store.ping()
    except Exception as exc:  # noqa: BLE001 - any failure means not ready
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "reason": type(exc).__name__},
        )
    return JSONResponse({"status": "ready"})
