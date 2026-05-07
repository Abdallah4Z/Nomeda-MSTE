import os
from fastapi import APIRouter, Depends

from ...schemas.session import SessionCreate, SessionResponse, SendSummaryRequest
from ...core.container import Container
from ..deps import get_container

router = APIRouter(prefix="/api", tags=["session"])


@router.post("/start")
async def start_session(
    body: SessionCreate,
    container: Container = Depends(get_container),
):
    session_id = container.session_manager.start(body.checkin)
    return SessionResponse(session_id=session_id)


@router.post("/session/end")
async def end_session(
    container: Container = Depends(get_container),
):
    summary = await container.session_manager.end()
    return summary


@router.get("/session/status")
async def session_status(
    container: Container = Depends(get_container),
):
    return {
        "running": container.session_manager.is_running,
        "session_id": container.session_manager.session_id,
        "duration_seconds": container.session_manager.get_duration_seconds(),
    }


@router.post("/session/send-summary")
async def send_summary(
    body: SendSummaryRequest,
    container: Container = Depends(get_container),
):
    try:
        import aiofiles
        import json as _json

        sessions_dir = container.settings.storage.sessions_dir
        summary_path = os.path.join(sessions_dir, f"summary_{container.session_manager.session_id}.json")
        async with aiofiles.open(summary_path, "w") as f:
            await f.write(_json.dumps(body.summary, indent=2, default=str))
        return {"status": "sent", "email": body.email}
    except Exception:
        return {"status": "error", "message": "Failed to save summary"}
