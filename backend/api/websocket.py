import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..core.state import system_state

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    last_pong = asyncio.get_running_loop().time()
    try:
        while True:
            try:
                state = system_state.snapshot()
                payload = {
                    "running": state.get("running", False),
                    "video_emotion": state.get("video_emotion"),
                    "voice_emotion": state.get("voice_emotion"),
                    "distress": state.get("distress"),
                    "stt_text": state.get("stt_text"),
                    "llm_response": state.get("llm_response"),
                    "tts_audio_url": state.get("tts_audio_url"),
                }
                await asyncio.wait_for(websocket.send_json(payload), timeout=5)
            except asyncio.TimeoutError:
                try:
                    pong = await asyncio.wait_for(websocket.receive(), timeout=3)
                    if pong.type == "websocket.pong":
                        last_pong = asyncio.get_running_loop().time()
                except asyncio.TimeoutError:
                    if asyncio.get_running_loop().time() - last_pong > 15:
                        break
                    continue
            await asyncio.sleep(1)
    except (WebSocketDisconnect, Exception):
        pass
