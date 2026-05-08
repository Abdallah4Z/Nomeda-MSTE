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
    webhook_url = container.settings.summary_webhook
    if not webhook_url:
        return {"status": "error", "message": "No webhook configured"}

    import json as _json
    import httpx

    payload = {
        "email": body.email,
        "session_id": container.session_manager.session_id,
        "summary": body.summary,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.is_success:
                return {"status": "sent", "email": body.email}
    except Exception:
        pass

    try:
        import aiofiles
        sessions_dir = container.settings.storage.sessions_dir
        fname = f"summary_{container.session_manager.session_id or 'unknown'}.json"
        async with aiofiles.open(os.path.join(sessions_dir, fname), "w") as f:
            await f.write(_json.dumps(payload, indent=2, default=str))
        return {"status": "saved_locally", "email": body.email}
    except Exception:
        return {"status": "error", "message": "Webhook unavailable and local save failed"}


@router.post("/session/delete")
async def delete_session(
    container: Container = Depends(get_container),
):
    sm = container.session_manager
    session_id = sm.session_id
    sm._current_session_id = None
    sm._start_time = None
    sm._messages = []
    sm._emotion_history = []
    sm._checkin = None

    system_state.set("running", False)
    system_state.set("session_id", None)

    # Delete saved session file if it exists
    import os as _os, glob as _glob
    sessions_dir = container.settings.storage.sessions_dir
    for f in _glob.glob(_os.path.join(sessions_dir, f"*{session_id or ''}*")):
        try: _os.remove(f)
        except: pass

    return {"status": "deleted", "session_id": session_id}
