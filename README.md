# Nomeda-MSTE — AI Multimodal Emotion Monitor & Therapist

A real-time AI-powered emotion monitoring and therapy system that fuses **facial expression analysis** (DeepFace + MediaPipe), **voice emotion recognition** (WavLM + HuBERT fusion), and **biometric data** (MAX30102 heart rate sensor) to detect emotional distress and provide empathetic AI therapist responses through an interactive web dashboard.

## Features

- **Real-Time Face Emotion Detection** — DeepFace (7 emotions) + MediaPipe FaceMesh (468 landmarks) + drowsiness/yawning/head nod detection
- **Voice Emotion Recognition (SER)** — WavLM + HuBERT fusion model for speech emotion classification
- **Speech-to-Text** — faster-whisper (tiny) for real-time transcription
- **Biometric Monitoring** — MAX30102 heart rate / SpO2 sensor via I2C (Arduino), with mock fallback
- **AI Therapist (LLM)** — FusionAgent combining all modalities; local Gemma 2B GGUF (primary) + Groq API (fallback) + FAISS RAG over therapy literature
- **Text-to-Speech** — Google Gemini Flash TTS (`gemini-3.1-flash-tts-preview`) with pyttsx3 fallback
- **Web Dashboard** — 3 modes: Live Monitoring, Video Session Analysis, 3D Avatar
- **Distress Score** — 0–100 gauge fusing multimodal input
- **Session Logging** — All data saved to CSV for later review
- **Docker Deployment** — Microservice architecture or monolithic image, NVIDIA GPU / Jetson support

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
| Biometrics | MAX30102 PPG sensor (I2C), Arduino firmware |
| Containerization | Docker, Docker Compose (multi-stage builds) |
| Hardware | USB cameras, microphones, serial/I2C sensors, NVIDIA GPU, Jetson |

## Architecture

**Native (single process)** — `main.py` spawns 4 threaded workers (video, voice, biometrics, fusion) with the FastAPI web app.

```
Camera ──► VideoEmotionAnalyzer ──┐
Mic    ──► VoiceEmotionAnalyzer ──┤──► FusionAgent (LLM) ──► TTS Engine
Sensor ──► BiometricProcessor  ───┘                          └──► SessionLogger
```

**Docker Microservices** — 4 containers orchestrated via Docker Compose:

```
Browser ──► web-api (:8010) ──► face-analysis (:8001)
           (orchestrator)   ──► voice-analysis (:8002)
                            ──► fusion-llm (:8003)
```

## Quick Start

### Docker (Recommended)

```bash
# One-time: build the base image (heavy deps: PyTorch, TF, DeepFace — ~20 min)
docker build -t ai-therapist-base:latest -f Dockerfile.base .

# Build and start all services
docker compose up -d --build

# Open the dashboard
open http://localhost:8010
```

### Native (No Docker)

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
| `SERIAL_PORT` | `/dev/ttyUSB0` | Biometric sensor serial port |
| `CAMERA_ID` | `0` | Camera device index |
| `CAMERA_SOURCE` | `browser` | `browser` (JS webcam) or `device` (USB) |
| `BIOMETRIC_SOURCE` | `auto` | `auto`, `max30102`, `serial`, or `mock` |

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
│   ├── biometrics/                  # MAX30102 + serial interface
│   └── output/                      # TTS engine + session logger
├── services/                        # Docker microservices
│   ├── web_api/                     # Orchestrator (port 8010)
│   ├── face_analysis/               # Face API (port 8001)
│   ├── voice_analysis/              # Voice API (port 8002)
│   └── fusion_llm/                  # LLM + TTS API (port 8003)
├── static/
│   ├── index.html                   # Web UI (3 modes)
│   └── js/                          # Frontend scripts + libs
├── tests/hardware_tests/            # Camera, audio, sensor tests
├── hardware/sensor_reader.ino       # Arduino MAX30102 firmware
├── LLM/                             # Standalone chatbot + RAG setup
├── Emotion Detection/               # Legacy DeepFace engine
├── docs/                            # Diagrams, reports, guides
├── Dockerfile                       # Monolithic image (CUDA 12.2)
├── Dockerfile.base                  # Base image (heavy deps)
├── docker-compose.yml               # Microservice orchestration
└── .env.example                     # Environment variable template
```

## Deployment Options

| Method | Command | Notes |
|--------|---------|-------|
| Docker (microservices) | `docker compose up -d` | 4 services, needs base image first |
| Docker (monolithic) | `docker build -t nomeda-mste . && docker run ...` | Single container |
| Native | `uvicorn web_app:app` | Direct Python, no containerization |
| Streamlit | `streamlit run live_dashboard.py` | Alternative UI |
| Jetson / Maven Kit | Docker export + load | Offline transfer via USB |

## License

Proprietary — All rights reserved.
