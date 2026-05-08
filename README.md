# Nomeda-MSTE — AI Emotion-Aware Therapist

A real-time multimodal AI therapy system that fuses facial expression recognition (DeepFace), voice emotion recognition (WavLM+HuBERT), and speech-to-text (faster-whisper) to provide empathetic AI therapist responses through an interactive web dashboard.

```
Camera ──► DeepFace ──► FERWorker (2 threads, 8-frame norm) ──┐
Mic    ──► Whisper STT ───────────────────────────────────────┤──► Groq LLM ──► TTS
         └─► WavLM+HuBERT SER ────────────────────────────────┘         └─► RAG (ChromaDB)
```

## Features

- **Real-Time FER** — 2-thread DeepFace worker, 8-frame rolling normalization, 7 emotions
- **Voice Emotion Recognition** — WavLM+HuBERT fusion, 8 emotions, chunked inference
- **Speech-to-Text** — faster-whisper (tiny) with WebM/Opus → WAV conversion
- **AI Therapist** — Groq LLM (llama-3.3-70b), therapeutic system prompt (Rogers + MI + CBT)
- **Short-Term Memory** — last 10 conversation exchanges included in each LLM call
- **RAG** — ChromaDB with 8,200+ chunks from therapy literature, relevance-filtered
- **Text-to-Speech** — Google Gemini TTS or pyttsx3 fallback
- **Interactive Face** — Canvas-based glowing digital face with mouth, eyebrows, 7 expressions
- **Live Dashboard** — Chat, camera feed, real-time emotion timeline, settings panel
- **Privacy Controls** — Anonymize or delete session data on end
- **Runtime Config** — Toggle FER/SER/TTS/Avatar on/off without restart

## Quick Start

```bash
pip install -r backend/requirements.txt
cp .env.example .env   # configure API keys
./run.sh               # starts via systemd
```

Open **http://localhost:8000/** in your browser.

## Tech Stack

| Category | Technology |
|----------|-----------|
| Backend   | FastAPI, Uvicorn, WebSockets |
| Frontend  | HTML5, CSS3, Vanilla JS, Chart.js, Canvas |
| FER       | DeepFace, OpenCV (Haar Cascade) |
| SER       | WavLM (`microsoft/wavlm-base-plus`), HuBERT (`facebook/hubert-base-ls960`) |
| STT       | faster-whisper (tiny, CTranslate2) |
| LLM       | Groq API (`llama-3.3-70b-versatile`) |
| RAG       | ChromaDB, SentenceTransformers (`all-MiniLM-L6-v2`) |
| TTS       | Google Gemini TTS or pyttsx3 |

## Architecture

### v3 Backend (Provider-Based)

```
backend/
├── main.py                    # FastAPI app, DI wiring
├── config/
│   ├── settings.py            # Pydantic env-based settings
│   └── runtime.py             # In-memory runtime config (API-changeable)
├── core/
│   ├── container.py           # DI container (wires providers)
│   ├── orchestrator.py        # Central coordinator
│   ├── session.py             # Session lifecycle + conversation memory
│   ├── state.py               # Thread-safe shared state singleton
│   └── events.py              # Pub/sub event bus
├── api/
│   ├── websocket.py           # WS state push (1s interval)
│   └── routes/
│       ├── session.py         # Start/end/delete/send-summary
│       ├── chat.py            # Chat with context + history
│       ├── media.py           # Frame upload, voice notes
│       ├── admin.py           # Status, history, models
│       ├── config.py          # Runtime config GET/PUT
│       └── tts.py             # TTS audio file serving
├── providers/
│   ├── base.py                # BaseProvider ABC
│   ├── llm/                   # Groq, OpenAI
│   ├── tts/                   # Gemini, pyttsx3
│   ├── stt/                   # faster-whisper
│   ├── ser/                   # WavLM+HuBERT fusion
│   ├── fer/                   # DeepFace + background worker
│   └── rag/                   # ChromaDB, hybrid FAISS
├── schemas/                   # Pydantic models
├── storage/                   # CSV/JSON session storage
└── utils/                     # Audio decode, logging
```

### Data Flow

```
User types "I feel anxious"
        │
POST /api/chat
        │
        ├── SessionManager stores message
        ├── Fetches face/voice emotions from SystemState
        ├── Retrieves last 10 exchanges (conversation memory)
        ├── RAG: searches ChromaDB → 3 most relevant therapy excerpts
        │      └── filtered by relevance_threshold (default 1.0)
        │
        ├── Builds LLM messages:
        │   [System Prompt] (therapist personality)
        │   [Reference Context] (emotions + RAG context)
        │   [History] (last 10 messages)
        │   [User Message]
        │
        ├── Groq API → generates therapy response + distress score
        │
        └── TTS → generates audio (if enabled + distress ≥ threshold)
        
Response: { response, distress, rag_sources, tts_audio }
```

### Facial Emotion Recognition (FER)

```
Browser (10fps JPEG)
        │
POST /api/browser-frame
        │
        ├── OpenCV face detection
        ├── Enqueue JPEG → FERWorker (2 background threads)
        │       ↙        ↘
        │   Thread 1    Thread 2
        │   (DeepFace)  (DeepFace)
        │       ↘        ↙
        │   ┌──────────────────┐
        │   │ 8-frame rolling  │
        │   │ window → mode    │
        │   └──────────────────┘
        │
        └── SystemState updated with latest normalized emotion
```

## Configuration

### Environment Variables

Prefix all with `NOMEDA_`. See `backend/config/settings.py` for defaults.

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key |
| `LLM__PROVIDER` | `groq` or `openai` |
| `LLM__MODEL` | Model name (default: `llama-3.3-70b-versatile`) |
| `LLM__TEMPERATURE` | Response creativity (default: `0.85`) |
| `TTS__PROVIDER` | `gemini` or `pyttsx3` |
| `GOOGLE_API_KEY` | Google AI key for Gemini TTS |
| `FER__FAST_MODE` | `true` = heuristic, `false` = DeepFace |
| `FER__NUM_THREADS` | Worker threads (default: `2`) |
| `FER__WINDOW_SIZE` | Normalization window (default: `8`) |
| `SER__PROVIDER` | `wavlm_hubert` or empty to disable |
| `STT__PROVIDER` | `faster_whisper` |
| `RAG__PROVIDER` | `chroma` or empty to disable |
| `SUMMARY_WEBHOOK` | n8n webhook URL for session emails |

### Runtime Config (changeable via UI)

Toggle FER, SER, TTS, Avatar, and adjust sliders from the Settings panel. All changes take effect immediately via `PUT /api/config` — no restart needed.

## Frontend

The dashboard is a single-page app with 4 screens:

1. **Check-in** — select mood emoji, optional voice note
2. **Chat** — live session with animated face, camera feed, chat, emotion timeline
3. **End Options** — privacy choices (anonymize or delete), download, email summary
4. **Full Summary** — session stats, JSON data, copy

### Face Animation

The canvas-based digital face has 7 expressions (neutral, happy, sad, angry, afraid, surprised, loved), a mouth that animates when talking, eyebrows that move per emotion, and a gentle sway when the user is speaking.

### Right Panel

- **Session** — real-time stats (duration, messages, distress, face/voice emotions)
- **Configuration** — toggle FER/SER/TTS/Avatar on/off, adjust sliders
- **System** — provider health status (6 services)

## API

16 endpoints + WebSocket. See `docs/BACKEND.md` for full reference.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/start` | Start session |
| POST | `/api/session/end` | End session |
| POST | `/api/session/delete` | Delete session data |
| POST | `/api/session/send-summary` | Email summary via webhook |
| GET | `/api/session/status` | Session status |
| POST | `/api/chat` | Send message, get AI response |
| POST | `/api/browser-frame` | Upload camera frame |
| POST | `/api/voice-note` | Upload voice recording |
| POST | `/api/browser-audio` | Upload browser audio |
| GET | `/api/tts/latest` | Get latest TTS audio |
| GET | `/api/admin/status` | System status |
| GET | `/api/admin/models` | Provider health |
| GET/PUT | `/api/config` | Runtime configuration |
| WS | `/ws` | Real-time state push (1s interval) |

## Performance

| Component | GPU Memory | Notes |
|-----------|-----------|-------|
| SentenceTransformer (RAG) | ~500MB | CUDA |
| WavLM + HuBERT (SER) | ~750MB | CUDA, background load |
| faster-whisper (STT) | ~1GB | CPU (int8) |
| DeepFace (FER) | ~6MB | CPU |
| **Total with all providers** | ~2.3GB / 4GB | GPU |

## License

Proprietary — All rights reserved.
