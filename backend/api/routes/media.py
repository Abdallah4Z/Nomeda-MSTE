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
    sm = container.session_manager
    if not sm or not sm.is_running:
        return {"status": "idle"}

    data = await frame.read()
    fer_provider = container.get_fer()

    if fer_provider:
        result = await fer_provider.predict(data)
        if result.face_detected:
            from ...core.state import system_state as _ss
            _ss.set("video_emotion", result.emotion)
            sm.add_emotion_point(
                face=result.emotion,
                confidence=result.confidence,
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

    emotion = result.get("emotion")
    if emotion:
        from ...core.state import system_state as _ss
        _ss.set("voice_emotion", emotion)

    sm = container.session_manager
    if sm and sm.is_running and emotion:
        sm.add_emotion_point(voice=emotion)

    return result


@router.post("/browser-audio")
async def browser_audio(
    audio: UploadFile = File(...),
    container: Container = Depends(get_container),
):
    sm = container.session_manager
    if not sm or not sm.is_running:
        return {"status": "idle"}

    data = await audio.read()
    result = await container.orchestrator.process_voice_note(data)
    return result
