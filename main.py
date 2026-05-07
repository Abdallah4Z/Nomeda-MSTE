"""
Nomeda Therapist — Full Multimodal Pipeline
Cam + Mic → FER + SER + STT → RAG-enhanced LLM → Qwen3-TTS
"""

import threading
import time
import json
import os

from modules.video.video_emotion import VideoEmotionAnalyzer
from modules.voice.voice_emotion import VoiceEmotionAnalyzer
from modules.voice.stt_engine import STTEngine
from modules.biometrics.heart_rate_processor import BiometricProcessor
from core.model.inference import FusionAgent
from modules.tts.qwen_tts import QwenTTS
from modules.output.session_logger import SessionLogger

# ── Config ────────────────────────────────────────────────────────────────────
TTS_BACKEND = os.getenv("TTS_BACKEND", "qwen").strip().lower()
USE_STT = os.getenv("USE_STT", "true").strip().lower() == "true"
FUSION_INTERVAL = float(os.getenv("FUSION_INTERVAL", "4.0"))

# ── Shared State ──────────────────────────────────────────────────────────────
system_state = {
    "face_emotion": "neutral",
    "voice_emotion": "neutral",
    "stt_text": "",
    "biometric_data": "",
    "last_user_text": "",
    "fusion_result": {"distress": 0, "response": "Initializing..."},
    "last_spoken_response": "",
}


# ── Modality Workers ──────────────────────────────────────────────────────────

def video_worker():
    global system_state
    try:
        analyzer = VideoEmotionAnalyzer()
        print("[Video] FER started")
        while True:
            system_state["face_emotion"] = analyzer.analyze_frame()
            time.sleep(0.5)
    except Exception as e:
        print(f"[Video] Error: {e}")


def voice_worker():
    global system_state
    try:
        analyzer = VoiceEmotionAnalyzer()
        print("[Voice] SER started")
        while True:
            system_state["voice_emotion"] = analyzer.analyze_audio()
            time.sleep(0.5)
    except Exception as e:
        print(f"[Voice] Error: {e}")


def stt_worker():
    global system_state
    if not USE_STT:
        print("[STT] Disabled")
        return
    try:
        engine = STTEngine(model_size="tiny", device="cuda")
        print("[STT] Started")
        # STT is typically triggered on-demand from the fusion worker
        # This worker maintains the engine; transcription happens in fusion_worker
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"[STT] Error: {e}")


def biometric_worker():
    global system_state
    try:
        source = os.getenv("BIOMETRIC_SOURCE", "auto").strip()
        processor = BiometricProcessor(source=source)
        print("[Biometric] Started")
        while True:
            system_state["biometric_data"] = processor.analyze_biometrics()
            time.sleep(1.0)
    except Exception as e:
        print(f"[Biometric] Error: {e}")


def fusion_worker():
    global system_state
    agent = FusionAgent()

    tts = None
    if TTS_BACKEND == "qwen":
        try:
            tts = QwenTTS(speaker="Ryan", language="English")
            print("[TTS] Qwen3-TTS ready")
        except Exception as e:
            print(f"[TTS] Qwen load failed: {e}")

    logger = SessionLogger()
    last_text = ""

    print("[Fusion] RAG + LLM engine started")
    while True:
        try:
            face_em = system_state["face_emotion"]
            voice_em = system_state["voice_emotion"]
            bio = system_state["biometric_data"]
            stt = system_state["stt_text"]

            user_said = stt or system_state.get("last_user_text", "")
            if user_said:
                last_text = user_said

            result = agent.fuse_inputs(
                face_emotion=face_em,
                voice_emotion=voice_em,
                biometric=bio,
                stt_text=user_said,
            )

            system_state["fusion_result"] = result
            print(f"\n── [Fusion] distress={result['distress']} | "
                  f"face={face_em} voice={voice_em}")
            print(f"  Nomeda: {result['response']}\n")

            logger.log_event({
                "face_emotion": face_em,
                "voice_emotion": voice_em,
                "stt_text": user_said,
                "fusion_result": result,
            })

            # Speak via Qwen TTS
            response = result.get("response", "")
            if tts and response and response != system_state["last_spoken_response"]:
                tts.speak(response, emotion_hint=face_em)
                system_state["last_spoken_response"] = response

            time.sleep(FUSION_INTERVAL)

        except Exception as e:
            print(f"[Fusion] Error: {e}")
            time.sleep(FUSION_INTERVAL)


def main():
    threads = [
        threading.Thread(target=video_worker, daemon=True, name="video"),
        threading.Thread(target=voice_worker, daemon=True, name="voice"),
        threading.Thread(target=biometric_worker, daemon=True, name="biometric"),
        threading.Thread(target=stt_worker, daemon=True, name="stt"),
        threading.Thread(target=fusion_worker, daemon=True, name="fusion"),
    ]

    for t in threads:
        t.start()

    print("\n" + "=" * 55)
    print("  NOMEDA THERAPIST — Full Multimodal Pipeline")
    print("  FER + SER + STT → RAG LLM → Qwen3-TTS")
    print("=" * 55)
    print("  Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Nomeda...")


if __name__ == "__main__":
    main()
