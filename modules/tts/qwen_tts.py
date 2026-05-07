"""
Qwen3-TTS integration module for Nomeda Therapist.
Uses Qwen3-TTS-12Hz-0.6B-CustomVoice for natural, low-latency speech synthesis.
"""

import os
import time
import base64
import threading
import wave
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

from modules.logging import get_logger
log = get_logger("tts")


TTS_OUTPUT_DIR = Path(os.getenv("TTS_OUTPUT_DIR", "data/tts"))
TTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _save_pcm_as_wav(filepath, arr, sr=24000):
    import numpy as np
    arr = (arr * 32767).astype(np.int16)
    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(arr.tobytes())


# ── Speaker map for emotional context ────────────────────────────────────────
EMOTION_SPEAKER_MAP = {
    "sad": "Serena",
    "anxious": "Vivian",
    "angry": "Ryan",
    "fear": "Vivian",
    "happy": "Aiden",
    "calm": "Serena",
    "neutral": "Ryan",
    "default": "Ryan",
}


class QwenTTS:
    def __init__(self, model_name: str = "",
                 device: str = "cuda:0",
                 dtype: str = "bfloat16",
                 speaker: str = "Ryan",
                 language: str = "English"):
        if not model_name:
            local = Path(__file__).resolve().parent.parent.parent / "models" / "qwen3-tts-0.6B"
            if local.exists():
                model_name = str(local)
            else:
                model_name = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
        self.model_name = model_name
        self.device = device
        self.dtype = dtype
        self.default_speaker = speaker
        self.language = language
        self._model = None
        self._load_failed = False
        self.is_speaking = False
        self.latest_audio_path: Optional[str] = None
        self.latest_mime_type = "audio/wav"

    def _load(self):
        if self._model is not None:
            return
        if self._load_failed:
            return
        try:
            from qwen_tts import Qwen3TTSModel
            import torch
            dtype_map = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}
            torch_dtype = dtype_map.get(self.dtype, torch.bfloat16)
            log.info(f" Loading {self.model_name}...")

            import torch
            cc = torch.cuda.get_device_capability()
            if cc[0] >= 8:
                attn = "flash_attention_2"
            elif cc[0] >= 7:
                attn = "sdpa"
                log.info(f" GPU compute {cc[0]}.{cc[1]} — using sdpa attention")
            else:
                attn = "eager"
                log.info(f" GPU compute {cc[0]}.{cc[1]} — using eager attention")

            self._model = Qwen3TTSModel.from_pretrained(
                self.model_name,
                device_map=self.device,
                dtype=torch_dtype,
                attn_implementation=attn,
            )
            log.info(f" Loaded successfully (device={self.device})")
        except ImportError:
            log.info("[QwenTTS] ERROR: qwen-tts package not installed. Run: pip install -U qwen-tts")
            self._load_failed = True
            raise
        except Exception as e:
            log.info(f" ERROR loading model: {e}")
            self._load_failed = True
            raise

    def load(self):
        self._load()

    def offload(self):
        import torch
        if self._model is not None:
            try:
                self._model = self._model.to("cpu")
            except AttributeError:
                self._model = None
            torch.cuda.empty_cache()
            log.info("[QwenTTS] Model offloaded to CPU")

    def _select_speaker(self, emotion_hint: str) -> str:
        emotion_hint = emotion_hint.lower().strip()
        for key, spk in EMOTION_SPEAKER_MAP.items():
            if key in emotion_hint:
                return spk
        return self.default_speaker

    def generate_sync(self, text: str, emotion_hint: str = "neutral",
                      language: Optional[str] = None) -> tuple:
        self._load()

        speaker = self._select_speaker(emotion_hint)
        lang = language or self.language

        t0 = time.time()
        try:
            wavs, sr = self._model.generate_custom_voice(
                text=text,
                language=lang,
                speaker=speaker,
            )
        except Exception as e:
            log.info(f"[QwenTTS] Generation error: {e}")
            return None, "audio/wav", None

        elapsed = time.time() - t0
        duration = len(wavs[0]) / sr if wavs else 0
        log.info(f"[QwenTTS] Generated {duration:.1f}s audio in {elapsed:.2f}s (RTF={elapsed/max(duration,0.1):.2f}x)")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"response_{ts}.wav"
        filepath = TTS_OUTPUT_DIR / filename
        _save_pcm_as_wav(filepath, wavs[0], sr)

        latest_path = TTS_OUTPUT_DIR / "latest.wav"
        _save_pcm_as_wav(latest_path, wavs[0], sr)

        self.latest_audio_path = str(filepath)

        with open(filepath, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        return str(latest_path), "audio/wav", audio_b64

    def speak(self, text: str, emotion_hint: str = "neutral",
              on_done: Optional[Callable] = None):
        if self._load_failed:
            log.info("[QwenTTS] Model load previously failed, skipping TTS.")
            if on_done:
                on_done(None, "audio/wav", None)
            return
        def run():
            try:
                filepath, mime, audio_b64 = self.generate_sync(text, emotion_hint)
                if on_done:
                    on_done(filepath, mime, audio_b64)
            except Exception as e:
                log.info(f"[QwenTTS] Speak error: {e}")
                if on_done:
                    on_done(None, "audio/wav", None)
            finally:
                self.is_speaking = False

        self.is_speaking = True
        threading.Thread(target=run, daemon=True).start()

    def get_latest_audio_path(self) -> Optional[str]:
        return self.latest_audio_path
