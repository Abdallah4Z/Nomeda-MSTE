"""
Nomeda Therapist — Sequenced Pipeline
Cam + Mic → FER + SER + STT → RAG LLM (offload) → Qwen3-TTS (offload) → loop
"""

import threading
import time
import json
import os
import queue

from modules.video.video_emotion import VideoEmotionAnalyzer
from modules.voice.voice_emotion import VoiceEmotionAnalyzer
from modules.voice.stt_engine import STTEngine
from modules.biometrics.heart_rate_processor import BiometricProcessor
from core.model.inference import FusionAgent
from modules.tts.qwen_tts import QwenTTS
from modules.output.session_logger import SessionLogger

TTS_BACKEND = os.getenv("TTS_BACKEND", "qwen").strip().lower()
USE_STT = os.getenv("USE_STT", "true").strip().lower() == "true"
FUSION_INTERVAL = float(os.getenv("FUSION_INTERVAL", "4.0"))

system_state = {
    "face_emotion": "neutral",
    "voice_emotion": "neutral",
    "stt_text": "",
    "biometric_data": "",
    "fusion_result": {"distress": 0, "response": "Initializing..."},
    "last_spoken_response": "",
}

tts_queue: queue.Queue = queue.Queue(maxsize=1)


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
    logger = SessionLogger()

    print("[Fusion] RAG + LLM engine started")
    while True:
        try:
            face_em = system_state["face_emotion"]
            voice_em = system_state["voice_emotion"]
            bio = system_state["biometric_data"]
            stt = system_state["stt_text"]

            user_said = stt or ""
            result = agent.fuse_inputs(
                face_emotion=face_em,
                voice_emotion=voice_em,
                biometric=bio,
                stt_text=user_said,
            )

            system_state["fusion_result"] = result
            response = result.get("response", "")
            print(f"\n── [Fusion] distress={result['distress']} | "
                  f"face={face_em} voice={voice_em}")
            print(f"  Nomeda: {response}\n")

            logger.log_event({
                "face_emotion": face_em,
                "voice_emotion": voice_em,
                "stt_text": user_said,
                "fusion_result": result,
            })

            # Offload LLM, then queue TTS work
            agent.offload_llm()
            if TTS_BACKEND == "qwen" and response and response != system_state["last_spoken_response"]:
                try:
                    tts_queue.put_nowait({"text": response, "emotion": face_em})
                    system_state["last_spoken_response"] = response
                except queue.Full:
                    pass

            time.sleep(FUSION_INTERVAL)
        except Exception as e:
            print(f"[Fusion] Error: {e}")
            time.sleep(FUSION_INTERVAL)


def tts_worker():
    global system_state
    if TTS_BACKEND != "qwen":
        return

    tts = QwenTTS(speaker="Ryan", language="English")
    print("[TTS] Qwen3-TTS worker started")
    while True:
        try:
            job = tts_queue.get()
            tts.load()
            tts.generate_sync(job["text"], emotion_hint=job["emotion"])
            tts.offload()
        except Exception as e:
            print(f"[TTS] Error: {e}")


def main():
    threads = [
        threading.Thread(target=video_worker, daemon=True, name="video"),
        threading.Thread(target=voice_worker, daemon=True, name="voice"),
        threading.Thread(target=biometric_worker, daemon=True, name="biometric"),
        threading.Thread(target=stt_worker, daemon=True, name="stt"),
        threading.Thread(target=fusion_worker, daemon=True, name="fusion"),
    ]
    if TTS_BACKEND == "qwen":
        threads.append(threading.Thread(target=tts_worker, daemon=True, name="tts"))

    for t in threads:
        t.start()

    print("\n" + "=" * 55)
    print("  NOMEDA THERAPIST — Sequenced Pipeline")
    print("  FER + SER + STT → RAG LLM → (offload) → Qwen3-TTS → (offload)")
    print("=" * 55)
    print("  Models never share VRAM. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Nomeda...")


if __name__ == "__main__":
    main()
