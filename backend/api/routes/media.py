import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form

from ...core.container import Container
from ..deps import get_container

router = APIRouter(prefix="/api", tags=["media"])


@router.post("/browser-frame")
async def browser_frame(
    frame: UploadFile = File(...),
    container: Container = Depends(get_container),
):
    data = await frame.read()
    fer_provider = container.get_fer()

    if fer_provider:
        result = await fer_provider.predict(data)
        sm = container.session_manager
        if sm and sm.is_running:
            sm.add_emotion_point(
                face=result.emotion,
                distress=0,
            )

    return {"status": "ok"}


@router.post("/voice-note")
async def voice_note(
    audio: UploadFile = File(...),
    container: Container = Depends(get_container),
):
    data = await audio.read()
    result = await container.orchestrator.process_voice_note(data)

    sm = container.session_manager
    if sm and sm.is_running and result.get("emotion"):
        sm.add_emotion_point(voice=result["emotion"])

    return result


@router.post("/browser-audio")
async def browser_audio(
    audio: UploadFile = File(...),
    container: Container = Depends(get_container),
):
    data = await audio.read()
    result = await container.orchestrator.process_voice_note(data)
    return result
