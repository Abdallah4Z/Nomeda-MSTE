import logging
import os
import warnings

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
EMOTIONS = ["anger", "calm", "disgust", "fear",
            "happy", "neutral", "sad", "surprised"]


class JointSER(nn.Module):
    def __init__(self):
        super().__init__()
        from transformers import WavLMModel, HubertModel

        self.wavlm = WavLMModel.from_pretrained(
            "microsoft/wavlm-base-plus", torch_dtype=torch.float32)
        self.hubert = HubertModel.from_pretrained(
            "facebook/hubert-base-ls960", torch_dtype=torch.float32)

        hidden = self.wavlm.config.hidden_size

        self.wavlm_proj = nn.Linear(hidden, hidden)
        self.hubert_proj = nn.Linear(hidden, hidden)
        self.attention_gate = nn.Sequential(
            nn.Linear(hidden * 2, 2))
        self.fusion_network = nn.Sequential(
            nn.Linear(hidden * 2, 768),
            nn.LayerNorm(768),
            nn.GELU(),
            nn.Dropout(0.19),
            nn.Linear(768, 384),
            nn.LayerNorm(384),
            nn.GELU(),
            nn.Dropout(0.19),
        )
        self.classifier = nn.Linear(384, 8)

    def forward(self, x):
        w = self.wavlm(x).last_hidden_state.mean(dim=1)
        h = self.hubert(x).last_hidden_state.mean(dim=1)
        w = self.wavlm_proj(w)
        h = self.hubert_proj(h)
        concat = torch.cat([w, h], dim=-1)
        gate = F.softmax(self.attention_gate(concat), dim=-1)
        w_gated = w * gate[:, 0:1]
        h_gated = h * gate[:, 1:2]
        combined = torch.cat([w_gated, h_gated], dim=-1)
        out = self.fusion_network(combined)
        return self.classifier(out)


class SERModel:
    name = "ser"

    def __init__(self, model_path: str):
        self._model_path = model_path
        self._model = None
        self._device = None

    def load(self):
        if self._model is not None:
            return

        if not os.path.exists(self._model_path):
            raise FileNotFoundError(f"SER weights not found at {self._model_path}")

        self._device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu")
        logger.info("Loading SER model on %s", self._device)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            checkpoint = torch.load(self._model_path, map_location="cpu",
                                    weights_only=False)
            sd = checkpoint["model_state_dict"]

        model = JointSER()

        missing, unexpected = model.load_state_dict(sd, strict=False)
        if missing:
            logger.warning("SER missing keys: %s", missing)
        if unexpected:
            logger.warning("SER unexpected keys: %s", unexpected)

        model.eval()
        model.to(self._device)
        self._model = model

        val = checkpoint.get("best_validation", {})
        ckpt_size = os.path.getsize(self._model_path) // 1024 // 1024
        logger.info("SER loaded (val_acc=%.1f%%, %dMB)",
                    val.get("accuracy", 0), ckpt_size)

    def unload(self):
        self._model = None
        if self._device and self._device.type == "cuda":
            torch.cuda.empty_cache()
        logger.info("SER model unloaded")

    @torch.no_grad()
    def predict(self, audio_bytes=None, audio_path=None):
        if self._model is None:
            raise RuntimeError("SER model not loaded — call load() first")

        waveform, sr = self._load_audio(audio_bytes, audio_path)
        if waveform is None:
            logger.warning("SER: could not load audio, returning zeros")
            return {e: 0.0 for e in EMOTIONS}

        if not isinstance(waveform, torch.Tensor):
            waveform = torch.from_numpy(waveform).float()
        if sr != SAMPLE_RATE:
            waveform = self._resample(waveform, sr, SAMPLE_RATE)
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0)

        if waveform.shape[-1] < SAMPLE_RATE * 0.3:
            pad = SAMPLE_RATE - waveform.shape[-1]
            waveform = F.pad(waveform, (0, pad), mode="constant")

        chunk_sec = 6
        stride_sec = 3
        max_len = SAMPLE_RATE * 30
        if waveform.shape[-1] > max_len:
            waveform = waveform[:, :max_len]

        chunk_len = SAMPLE_RATE * chunk_sec
        stride_len = SAMPLE_RATE * stride_sec
        if waveform.shape[-1] > chunk_len:
            chunks = []
            for start in range(0, waveform.shape[-1] - chunk_len + 1,
                               stride_len):
                chunks.append(waveform[:, start:start + chunk_len])
            logits = []
            for c in chunks:
                c = c.to(self._device)
                logits.append(self._model(c))
            logits = torch.stack(logits).mean(dim=0)
        else:
            waveform = waveform.to(self._device)
            if waveform.shape[-1] < chunk_len:
                pad = chunk_len - waveform.shape[-1]
                waveform = F.pad(waveform, (0, pad), mode="constant")
            logits = self._model(waveform)

        probs = F.softmax(logits, dim=-1).cpu().numpy().flatten()
        result = {EMOTIONS[i]: round(float(probs[i]), 4)
                  for i in range(len(EMOTIONS))}
        logger.debug("SER: %s", result)
        return result

    def _load_audio(self, audio_bytes, audio_path):
        import tempfile
        from pydub import AudioSegment

        path = audio_path
        cleanup = False

        if audio_bytes:
            tmp = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
            tmp.write(audio_bytes)
            tmp.close()
            raw_path = tmp.name
            wav_path = raw_path + ".wav"
            try:
                AudioSegment.from_file(raw_path).export(
                    wav_path, format="wav")
                path = wav_path
                cleanup = True
            except Exception as e:
                logger.error("Audio conversion failed: %s", e)
                return None, None
            finally:
                if os.path.exists(raw_path):
                    os.unlink(raw_path)
        else:
            wav_path = path + ".wav" if path else None
            if path and not path.endswith(".wav"):
                try:
                    AudioSegment.from_file(path).export(
                        wav_path, format="wav")
                    path = wav_path
                    cleanup = True
                except Exception:
                    pass

        if path is None:
            return None, None

        try:
            import soundfile as sf
            waveform, sr = sf.read(path, dtype="float32")
            if waveform.ndim == 2:
                waveform = waveform.mean(axis=1)
            return waveform, sr
        except Exception as e:
            logger.error("Audio load failed: %s", e)
            return None, None
        finally:
            if cleanup and os.path.exists(path):
                os.unlink(path)

    @staticmethod
    def _resample(waveform, orig_sr, target_sr):
        import torchaudio.functional as AF
        if not isinstance(waveform, torch.Tensor):
            waveform = torch.from_numpy(waveform).float()
        if waveform.ndim == 1:
            waveform = waveform.unsqueeze(0)
        return AF.resample(waveform, orig_sr, target_sr)
