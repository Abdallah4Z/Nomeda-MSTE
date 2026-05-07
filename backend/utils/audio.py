import io
import subprocess
from typing import Optional


def decode_audio(audio_data: bytes, target_sr: int = 16000, target_format: str = "wav") -> Optional[bytes]:
    try:
        proc = subprocess.run(
            ["ffmpeg", "-i", "pipe:0",
             "-f", target_format,
             "-acodec", "pcm_s16le",
             "-ar", str(target_sr),
             "-ac", "1",
             "pipe:1"],
            input=audio_data,
            capture_output=True,
            timeout=30,
        )
        if proc.returncode == 0:
            return proc.stdout
    except Exception:
        pass
    return None


def resample_audio(audio_data: bytes, src_sr: int, target_sr: int = 16000) -> Optional[bytes]:
    try:
        proc = subprocess.run(
            ["ffmpeg", "-f", "s16le", "-ar", str(src_sr), "-ac", "1", "-i", "pipe:0",
             "-f", "wav", "-acodec", "pcm_s16le", "-ar", str(target_sr), "-ac", "1",
             "pipe:1"],
            input=audio_data,
            capture_output=True,
            timeout=30,
        )
        if proc.returncode == 0:
            return proc.stdout
    except Exception:
        pass
    return None


def audio_to_numpy(audio_data: bytes, sample_rate: int = 16000):
    import numpy as np
    import soundfile as sf
    buf = io.BytesIO(audio_data)
    data, sr = sf.read(buf)
    if sr != sample_rate:
        import librosa
        data = librosa.resample(data, orig_sr=sr, target_sr=sample_rate)
    return data
