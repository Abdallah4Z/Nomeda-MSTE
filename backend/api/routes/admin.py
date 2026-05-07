from fastapi import APIRouter, Depends

from ...schemas.admin import SystemStatus
from ...core.container import Container
from ..deps import get_container

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/status")
async def admin_status(
    container: Container = Depends(get_container),
):
    sm = container.session_manager
    store = container.store

    total = 0
    recent = []
    if store:
        total = await store.get_total_count()
        recent = await store.get_recent_sessions(5)

    provider_statuses = container.all_provider_statuses()
    models_ready = sum(1 for p in provider_statuses if p.get("status") == "ready")
    models_total = len(provider_statuses)

    avg_distress_val = None
    if sm and sm.is_running:
        stats = sm._calc_stats()
        avg_distress_val = stats.get("avg_distress")

    return SystemStatus(
        running=sm.is_running if sm else False,
        total_sessions=total,
        avg_distress=avg_distress_val,
        models_ready=models_ready,
        models_total=models_total,
        recent_sessions=recent,
    )


@router.get("/config")
async def get_config(
    container: Container = Depends(get_container),
):
    cfg = container.settings
    return {
        "llm_mode": cfg.llm.provider,
        "max_tokens": cfg.llm.max_tokens,
        "temperature": cfg.llm.temperature,
        "tts_backend": cfg.tts.provider,
        "tts_threshold": cfg.tts.distress_threshold,
        "camera_source": cfg.camera_source,
        "camera_id": cfg.camera_id,
        "groq_key": "configured" if cfg.groq_api_key else None,
    }


@router.post("/config")
async def save_config(
    body: dict,
    container: Container = Depends(get_container),
):
    return {"status": "saved"}


@router.get("/history")
async def get_history(
    container: Container = Depends(get_container),
):
    if not container.store:
        return {"sessions": []}
    sessions = await container.store.list_sessions(100)
    return {"sessions": sessions}


@router.get("/history/{session_id}")
async def get_session_detail(
    session_id: str,
    container: Container = Depends(get_container),
):
    if not container.store:
        return None
    data = await container.store.get_session(session_id)
    if not data:
        return {"error": "Session not found"}
    return data


@router.get("/logs")
async def get_logs(
    level: str = "all",
):
    return {"logs": []}


@router.get("/models")
async def get_models(
    container: Container = Depends(get_container),
):
    statuses = container.all_provider_statuses()
    return {"models": statuses}
