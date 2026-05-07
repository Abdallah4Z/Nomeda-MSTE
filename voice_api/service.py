import io
import os
import sys
import time
import threading
import numpy as np
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Resolve model paths relative to project root (two levels up if in voice_api/)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)  # /home/.../Hackathon

def _resolve_model_path(env_key, default_rel):
    env_val = os.getenv(env_key, "")
    if env_val and os.path.exists(env_val):
        return env_val
    abs_path = os.path.join(_project_root, default_rel)
    if os.path.exists(abs_path):
        return abs_path
    return os.path.join(_project_root, default_rel)  # let it fail naturally

from ser_model import SERInference, NUM_SAMPLES

app = FastAPI(title="Voice Emotion API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

SAMPLE_RATE = 16000
API_KEY = os.getenv("VOICE_API_KEY", "")
ser = None
_lock = threading.Lock()


def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key


@app.on_event("startup")
def startup():
    global ser
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[VoiceAPI] Device: {device}")
    ser = SERInference(
        model_path=_resolve_model_path("SER_MODEL_PATH", "models/ser/wavlm_hubert_optimized_seed456.pth"),
        fallback_path=_resolve_model_path("SER_FALLBACK_PATH", "models/FINAL_BEST_seed456.pth"),
    )
    print(f"[VoiceAPI] Ready. API key auth: {'enabled' if API_KEY else 'disabled'}")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "ser_loaded": ser is not None and ser.model is not None,
    }


@app.post("/ser")
async def speech_emotion(audio: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    """Speech emotion recognition. Requires X-API-Key header if VOICE_API_KEY is set."""
    if ser is None or ser.model is None:
        return JSONResponse(content={"error": "ser_not_ready"}, status_code=503)

    content = await audio.read()
    if not content:
        return JSONResponse(content={"error": "empty_audio"}, status_code=400)

    try:
        audio_np = np.frombuffer(content, dtype=np.int16).astype(np.float32) / 32768.0
    except Exception:
        return JSONResponse(content={"error": "invalid_audio_format"}, status_code=400)

    try:
        emotion, confidence = ser.predict(audio_np, sr=SAMPLE_RATE)
        return {"emotion": emotion, "confidence": round(confidence, 4)}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/analyze")
async def analyze_audio(audio: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    """Analyze audio for emotion. Requires X-API-Key header if VOICE_API_KEY is set."""
    if ser is None or ser.model is None:
        return JSONResponse(content={"error": "ser_not_ready"}, status_code=503)

    content = await audio.read()
    if not content:
        return JSONResponse(content={"error": "empty_audio"}, status_code=400)

    try:
        audio_np = np.frombuffer(content, dtype=np.int16).astype(np.float32) / 32768.0
    except Exception:
        return JSONResponse(content={"error": "invalid_audio_format"}, status_code=400)

    if len(audio_np) < SAMPLE_RATE * 0.5:
        return JSONResponse(content={"error": "audio_too_short"}, status_code=400)

    with _lock:
        emotion, confidence = ser.predict(audio_np, sr=SAMPLE_RATE)
        emotion = emotion if emotion not in ("Unavailable", "Error") else "Neutral"

    return {"emotion": emotion, "confidence": round(confidence, 4)}


if __name__ == "__main__":
    port = int(os.getenv("VOICE_API_PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
