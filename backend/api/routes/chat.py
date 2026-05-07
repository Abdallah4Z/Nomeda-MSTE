from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ...schemas.chat import ChatRequest, ChatResponse
from ...core.container import Container
from ...core.state import system_state
from ..deps import get_container

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(
    body: ChatRequest,
    container: Container = Depends(get_container),
):
    sm = container.session_manager
    if not sm or not sm.is_running:
        return ChatResponse(response="Please start a session first.")

    sm.add_message("user", body.message)

    state = system_state.snapshot()
    face_emotion = state.get("video_emotion")
    voice_emotion = state.get("voice_emotion")
    distress = state.get("distress")

    result = await container.orchestrator.process_chat_message(
        text=body.message,
        face_emotion=face_emotion,
        voice_emotion=voice_emotion,
        distress=distress,
    )

    return JSONResponse(content=result)
