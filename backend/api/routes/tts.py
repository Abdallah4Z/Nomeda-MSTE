import os
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ...core.container import Container
from ..deps import get_container

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.get("/latest")
async def get_latest_tts(
    container: Container = Depends(get_container),
):
    tts_dir = container.settings.storage.tts_dir
    path = os.path.join(tts_dir, "latest.wav")
    if os.path.exists(path):
        return FileResponse(path, media_type="audio/wav")
    return {"error": "No TTS file available"}
