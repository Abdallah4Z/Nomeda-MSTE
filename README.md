# Nomeda-MSTE — AI Emotion Monitor & Therapist

A real-time AI-powered emotion monitoring and therapy system that fuses **facial expression analysis** (DeepFace + MediaPipe) and **voice emotion recognition** (WavLM + HuBERT fusion) to detect emotional distress and provide empathetic AI therapist responses through an interactive web dashboard.

## Features

- **Real-Time Face Emotion Detection** — DeepFace (7 emotions) + MediaPipe FaceMesh (468 landmarks) + drowsiness/yawning/head nod detection
- **Voice Emotion Recognition (SER)** — WavLM + HuBERT fusion model for speech emotion classification
- **Speech-to-Text** — faster-whisper (tiny) for real-time transcription
- **AI Therapist (LLM)** — FusionAgent combining all modalities; local Gemma 2B GGUF (primary) + Groq API (fallback) + FAISS RAG over therapy literature
- **Text-to-Speech** — Google Gemini Flash TTS (`gemini-2.0-flash-tts-preview`) with pyttsx3 fallback
- **Web Dashboard** — 3 modes: Live Monitoring, Video Session Analysis, 3D Avatar
- **Distress Score** — 0–100 gauge fusing multimodal input
- **Session Logging** — All data saved to CSV for later review

## Tech Stack

| Category | Technologies |
|----------|-------------|
| Backend | FastAPI, Uvicorn, WebSockets, MJPEG streaming |
| Frontend | HTML5, CSS3, Vanilla JS, Chart.js, Three.js (3D avatar) |
| Face Analysis | DeepFace, MediaPipe FaceMesh, OpenCV |
| Voice Analysis | WavLM (`microsoft/wavlm-base-plus`), HuBERT (`facebook/hubert-base-ls960`), faster-whisper |
| LLM | Gemma 2B GGUF (`llama-cpp-python`), Groq API (fallback) |
| RAG | FAISS, SentenceTransformers (`all-MiniLM-L6-v2`) |
| TTS | Google Gemini Flash TTS, pyttsx3 (fallback) |

## Architecture

`web_app.py` spawns threaded workers (video, voice, fusion) and serves the FastAPI web app.

```
Camera ──► VideoEmotionAnalyzer ──┐
Mic    ──► VoiceEmotionAnalyzer ──┤──► FusionAgent (LLM) ──► TTS Engine
                                   └──► SessionLogger
```

## Quick Start

### Native

```bash
pip install -r requirements.txt
uvicorn web_app:app --host 0.0.0.0 --port 8000
```

### Streamlit Dashboard

```bash
streamlit run live_dashboard.py   # Full AI therapist UI
streamlit run dashboard.py        # Session log viewer
```

## Web Dashboard — 3 Modes

1. **Live Monitoring** — Real-time camera feed, emotion metrics, distress gauge, session history sidebar, AI therapist chat
2. **Video Session** — Upload or record a video for batch analysis with emotion timeline
3. **Avatar** — 3D Three.js avatar that mirrors your detected emotional state

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | Groq API key (fallback LLM) |
| `LLM_MODE` | `local` | `local` (Gemma GGUF) or `api` (Groq) |
| `GOOGLE_API_KEY` | — | Google AI key for Gemini TTS |
| `TTS_BACKEND` | `gemini` | `gemini` or `local` (pyttsx3) |
| `TTS_DISTRESS_THRESHOLD` | `0` | Minimum distress score to trigger TTS |
| `CAMERA_ID` | `0` | Camera device index |
| `CAMERA_SOURCE` | `browser` | `browser` (JS webcam) or `device` (USB) |

The system runs without API keys (local LLM + TTS fallback). Gemini TTS and Groq LLM are optional upgrades.

## Project Structure

```
├── web_app.py                       # FastAPI web app (all-in-one)
├── main.py                          # Native threaded orchestrator
├── live_dashboard.py                # Streamlit AI therapist UI
├── dashboard.py                     # Streamlit log viewer
├── core/
│   ├── model/inference.py           # FusionAgent (LLM + RAG)
│   └── rag/                         # FAISS vector retrieval
├── modules/
│   ├── video/                       # DeepFace + MediaPipe analyzers
│   ├── voice/                       # WavLM/HuBERT SER + Whisper STT
│   └── output/                      # TTS engine + session logger
├── static/
│   ├── index.html                   # Web UI (3 modes)
│   └── js/                          # Frontend scripts + libs
├── LLM/                             # Standalone chatbot + RAG setup
├── docs/                            # Diagrams, reports, guides
├── scripts/                         # Utility scripts
└── .env.example                     # Environment variable template
```

## License

Proprietary — All rights reserved.
