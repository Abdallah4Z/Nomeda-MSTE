# Nomeda-MSTE — Backend & API Documentation

## Architecture Overview

```
Browser ── HTTP ──► FastAPI ──► Container ──► Providers
                        │                        │
                        ├── SessionManager        ├── LLM (Groq/OpenAI)
                        ├── Orchestrator          ├── TTS (Gemini/pyttsx3)
                        ├── EventBus              ├── STT (faster-whisper)
                        ├── RuntimeConfig         ├── SER (WavLM+HuBERT)
                        └── SystemState           ├── FER (DeepFace)
                                                   └── RAG (ChromaDB)
```

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| `Container` | `backend/core/container.py` | DI container — wires all providers, session, orchestrator |
| `Orchestrator` | `backend/core/orchestrator.py` | Central coordinator — chat messages, frame processing, voice notes |
| `SessionManager` | `backend/core/session.py` | Session lifecycle — start/end, message history, emotion tracking |
| `EventBus` | `backend/core/events.py` | Pub/sub event system for internal communication |
| `SystemState` | `backend/core/state.py` | Thread-safe singleton for shared real-time state |
| `RuntimeConfig` | `backend/config/runtime.py` | In-memory config store, get/set via API, no restart needed |

### Provider System

All providers extend `BaseProvider` in `backend/providers/base.py`:

```python
class BaseProvider(ABC):
    async def startup(self)    # Initialize (called at app startup)
    async def shutdown(self)   # Cleanup (called at app shutdown)
    async def health(self) -> ProviderStatus  # Readiness check
```

| Provider | File | Backend | Status |
|----------|------|---------|--------|
| `GroqLLMProvider` | `providers/llm/groq.py` | Groq API (llama-3.3-70b) | ✅ |
| `OpenAILikeLLMProvider` | `providers/llm/openai.py` | OpenAI API (or any OpenAI-compatible) | ✅ |
| `GeminiTTSProvider` | `providers/tts/gemini.py` | Google Gemini TTS API | ✅ |
| `Pyttsx3TTSProvider` | `providers/tts/pyttsx3.py` | Local pyttsx3 (offline) | ✅ |
| `FasterWhisperSTTProvider` | `providers/stt/faster_whisper.py` | faster-whisper (CTranslate2) | ✅ |
| `WavlmHubertSERProvider` | `providers/ser/wavlm_hubert.py` | WavLM + HuBERT fusion | ✅ |
| `DeepFaceFERProvider` | `providers/fer/deepface.py` | DeepFace + OpenCV | ✅ |
| `ChromaRAGProvider` | `providers/rag/chroma.py` | ChromaDB + SentenceTransformer | ✅ |
| `HybridFaissRAGProvider` | `providers/rag/hybrid_faiss.py` | FAISS + BM25 hybrid | ✅ |

---

## API Endpoints

### Session

#### `POST /api/start`
Start a new session.

**Request:**
```json
{
  "checkin": {
    "emotion": "sad",
    "text": "I've been feeling down lately"
  }
}
```

**Response:** `200 OK`
```json
{
  "session_id": "sess_a1b2c3d4e5f6",
  "status": "running"
}
```

---

#### `POST /api/session/end`
End the current session and save summary.

**Request:** (empty body)

**Response:** `200 OK`
```json
{
  "session_id": "sess_a1b2c3d4e5f6",
  "duration_seconds": 245,
  "checkin": { "emotion": "sad", "text": "..." },
  "messages": [
    { "role": "user", "text": "I feel sad", "timestamp": "..." },
    { "role": "ai", "text": "I hear you...", "timestamp": "...", "fusion": {...} }
  ],
  "emotion_timeline": [...],
  "stats": {
    "message_count": 5,
    "avg_distress": 42,
    "dominant_emotion": "sad"
  },
  "timestamp": "2026-05-08T..."
}
```

---

#### `GET /api/session/status`
Check current session state.

**Response:** `200 OK`
```json
{
  "running": true,
  "session_id": "sess_a1b2c3d4e5f6",
  "duration_seconds": 120
}
```

---

#### `POST /api/session/send-summary`
Send session summary via webhook (or save locally as fallback).

**Request:**
```json
{
  "email": "user@example.com",
  "summary": { "session_id": "...", "messages": [...], ... }
}
```

**Response:** `200 OK`
```json
{ "status": "sent", "email": "user@example.com" }
```

---

#### `POST /api/session/delete`
Permanently delete all session data.

**Request:** (empty body)

**Response:** `200 OK`
```json
{ "status": "deleted", "session_id": "sess_a1b2c3d4e5f6" }
```

---

### Chat

#### `POST /api/chat`
Send a message and get AI therapist response with multimodal context.

**Request:**
```json
{
  "message": "I feel anxious about work"
}
```

**Response:** `200 OK`
```json
{
  "response": "It sounds like you're carrying a lot on your shoulders...",
  "face_emotion": "sad",
  "voice_emotion": "neutral",
  "distress": 60,
  "rag_sources": [
    {
      "text": "Cognitive restructuring involves...",
      "score": 0.885,
      "metadata": { "source": "CBT Handbook.pdf" }
    }
  ],
  "tts_audio_url": "/api/tts/latest",
  "tts_audio_b64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQ..."
}
```

---

### Media

#### `POST /api/browser-frame`
Send a camera frame for facial emotion recognition.

**Request:** `multipart/form-data`
```
frame: <JPEG image bytes>
```

**Response:** `200 OK`
```json
{ "status": "ok" }
```

Returns `{ "status": "idle" }` when no session is active.

---

#### `POST /api/voice-note`
Send a recorded voice note for STT + SER.

**Request:** `multipart/form-data`
```
audio: <WebM audio bytes>
```

**Response:** `200 OK`
```json
{
  "transcript": "I feel really anxious today",
  "emotion": "Fear"
}
```

---

#### `POST /api/browser-audio`
Send continuous browser audio for STT + SER (used during active session).

**Request:** `multipart/form-data`
```
audio: <raw PCM bytes>
```

**Response:** `200 OK`
```json
{
  "transcript": "",
  "emotion": "Neutral"
}
```

Returns `{ "status": "idle" }` when no session is active.

---

### TTS

#### `GET /api/tts/latest`
Get the most recently generated TTS audio file.

**Response:** `200 OK` — `audio/wav` binary file

---

### Admin

#### `GET /api/admin/status`
Get system status summary.

**Response:** `200 OK`
```json
{
  "running": false,
  "total_sessions": 12,
  "avg_distress": 34,
  "models_ready": 4,
  "models_total": 6,
  "recent_sessions": [...]
}
```

---

#### `GET /api/admin/models`
Get health status of all providers.

**Response:** `200 OK`
```json
{
  "models": [
    { "name": "llm", "status": "ready", "description": "" },
    { "name": "tts", "status": "ready", "description": "" },
    { "name": "stt", "status": "ready", "description": "" },
    { "name": "ser", "status": "error", "description": "SER not loaded" },
    { "name": "fer", "status": "ready", "description": "" },
    { "name": "rag", "status": "ready", "description": "" }
  ]
}
```

---

#### `GET /api/admin/history`
List all session summaries.

**Response:** `200 OK`
```json
{ "sessions": [{ "session_id": "...", "timestamp": "..." }, ...] }
```

---

#### `GET /api/admin/history/{session_id}`
Get a specific session's full data.

---

#### `GET /api/admin/config`
Get current configuration values (env-based).

---

#### `POST /api/admin/config`
Update configuration values at runtime.

---

### Configuration (Runtime)

#### `GET /api/config`
Return all runtime configuration values.

**Response:** `200 OK`
```json
{
  "rag.relevance_threshold": 1.0,
  "ws.push_interval_ms": 1000,
  "camera.frame_interval_ms": 100,
  "audio.chunk_size": 4096,
  "tts.enabled": true,
  "tts.auto_play": true,
  "fer.enabled": true,
  "ser.enabled": true,
  "avatar.enabled": true,
  "session.max_duration_min": 0,
  "emotion.history_max": 200,
  "timeline.max_points": 60,
  "face.anim_speed_ms": 700
}
```

---

#### `GET /api/config/{key}`
Get a single config value.

**Response:** `200 OK`
```json
{ "tts.auto_play": true }
```

---

#### `PUT /api/config`
Update one or more runtime config values.

**Request:**
```json
{ "tts.auto_play": false, "fer.enabled": false }
```

**Response:** `200 OK`
```json
{
  "updated": ["tts.auto_play", "fer.enabled"],
  "failed": []
}
```

All changes take effect immediately — no restart needed.

---

### WebSocket

#### `WS /ws`
Real-time state push — sends a JSON payload every 1 second.

**Message format:**
```json
{
  "running": true,
  "video_emotion": "sad",
  "voice_emotion": "neutral",
  "distress": 42,
  "stt_text": "",
  "llm_response": "",
  "tts_audio_url": null
}
```

---

## Configuration

### Environment Variables (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `NOMEDA_GROQ_API_KEY` | — | Groq API key for LLM |
| `NOMEDA_LLM__PROVIDER` | `groq` | LLM backend: `groq` or `openai` |
| `NOMEDA_LLM__MODEL` | `llama-3.3-70b-versatile` | Model name |
| `NOMEDA_LLM__TEMPERATURE` | `0.85` | Response creativity |
| `NOMEDA_LLM__MAX_TOKENS` | `1024` | Max response length |
| `NOMEDA_LLM__SYSTEM_PROMPT` | see settings.py | Therapist system prompt |
| `NOMEDA_GOOGLE_API_KEY` | — | Google AI key for Gemini TTS |
| `NOMEDA_TTS__PROVIDER` | `pyttsx3` | TTS backend: `gemini` or `pyttsx3` |
| `NOMEDA_TTS__MODEL` | `gemini-2.5-flash-preview-tts` | Gemini TTS model |
| `NOMEDA_TTS__DISTRESS_THRESHOLD` | `0` | Min distress to trigger TTS |
| `NOMEDA_SER__PROVIDER` | `wavlm_hubert` | SER backend |
| `NOMEDA_SER__MODEL_PATH` | `models/ser/...pth` | Path to SER checkpoint |
| `NOMEDA_FER__PROVIDER` | `deepface` | FER backend |
| `NOMEDA_FER__FAST_MODE` | `false` | Use heuristic vs DeepFace |
| `NOMEDA_FER__NUM_THREADS` | `2` | FER worker threads |
| `NOMEDA_FER__WINDOW_SIZE` | `8` | Emotion normalization window |
| `NOMEDA_STT__PROVIDER` | `faster_whisper` | STT backend |
| `NOMEDA_STT__MODEL_SIZE` | `tiny` | Whisper model size |
| `NOMEDA_RAG__PROVIDER` | `chroma` | RAG backend |
| `NOMEDA_OPENAI_API_KEY` | — | OpenAI API key (alternative LLM) |
| `NOMEDA_SUMMARY_WEBHOOK` | — | Webhook URL for session summaries |
| `NOMEDA_CAMERA_ID` | `0` | Camera device index |
| `NOMEDA_DEBUG` | `false` | Enable debug logging |

### Runtime Configuration

Changed via `PUT /api/config` — takes effect immediately.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `fer.enabled` | bool | `true` | Enable facial emotion recognition |
| `ser.enabled` | bool | `true` | Enable speech emotion recognition |
| `tts.enabled` | bool | `true` | Enable TTS audio generation |
| `tts.auto_play` | bool | `true` | Auto-play TTS audio on response |
| `avatar.enabled` | bool | `true` | Show/hide the robot face animation |
| `rag.relevance_threshold` | float | `1.0` | RAG result relevance cutoff |
| `camera.frame_interval_ms` | int | `100` | Frame capture interval |
| `face.anim_speed_ms` | int | `700` | Face animation duration |
| `ws.push_interval_ms` | int | `1000` | WebSocket push interval |
| `session.max_duration_min` | int | `0` | Max session duration (0 = unlimited) |
| `emotion.history_max` | int | `200` | Max emotion history points |
| `timeline.max_points` | int | `60` | Max timeline chart points |

---

## Data Flow

### Chat Message Flow

```
User types message
        │
        ▼
POST /api/chat { message: "I feel anxious" }
        │
        ├──► SessionManager.add_message("user", text)
        ├──► SystemState.snapshot() → get face/voice emotions
        ├──► get_conversation_history() → last 10 exchanges
        │
        ├──► RAG: search chroma for relevant therapy context
        │       └── filter by relevance_threshold
        │
        ├──► Orchestrator.process_chat_message()
        │       │
        │       ├── Build messages: [history] + [context] + [user message]
        │       │
        │       ├──► LLM.generate_with_context()
        │       │       ├── System prompt (therapist personality)
        │       │       ├── Reference context (RAG + emotions)
        │       │       ├── Conversation history
        │       │       └── User message
        │       │       └──► Groq API → { response, distress }
        │       │
        │       ├── SessionManager.add_message("ai", response)
        │       │
        │       └──► TTS.synthesize(response)  [if enabled + distress >= threshold]
        │               └──► Gemini API → audio/wav
        │
        └──◄ Response: { response, distress, rag_sources, tts_audio }
```

### FER (Face Emotion) Flow

```
Browser webcam (10fps)
        │
        ▼
POST /api/browser-frame (JPEG bytes)
        │
        ├── Session guard (skip if no session)
        │
        ├── DeepFaceFERProvider.predict()
        │       ├── Decode JPEG → OpenCV face detection
        │       ├── Enqueue to FERWorker (2 background threads)
        │       └── Return latest normalized emotion immediately
        │
        ├── SystemState.set("video_emotion", result)
        └── SessionManager.add_emotion_point(face=emotion)

FERWorker (background):
        ┌─────────────────┐
        │  Frame Queue     │  ← incoming JPEGs
        └────────┬────────┘
              ↙     ↘
        Thread 1   Thread 2
        (DeepFace)  (DeepFace)
              ↘     ↙
        ┌────────┬────────┐
        │ 8-frame window │
        │  mode = most    │
        │  common emotion │
        └────────┬────────┘
                 ▼
        latest_emotion updated
```

### SER (Voice Emotion) Flow

```
User holds mic → records → releases
        │
        ▼
POST /api/voice-note (WebM audio)
        │
        ├── Orchestrator.process_voice_note()
        │       ├── STT.transcribe() → text
        │       └── SER.predict() → emotion probabilities
        │
        ├── SystemState.set("voice_emotion", emotion)
        └── SessionManager.add_emotion_point(voice=emotion)
```

---

## Directory Structure

```
backend/
├── main.py                        # FastAPI app entry point, DI wiring
├── requirements.txt               # Python dependencies
├── config/
│   ├── settings.py                # Pydantic Settings (env-based)
│   └── runtime.py                 # RuntimeConfig (API-changeable)
├── core/
│   ├── container.py               # DI container
│   ├── orchestrator.py            # Central coordinator
│   ├── session.py                 # Session lifecycle
│   ├── state.py                   # Thread-safe shared state
│   └── events.py                  # Pub/sub event bus
├── api/
│   ├── deps.py                    # FastAPI dependency injection
│   ├── websocket.py               # WebSocket state push
│   └── routes/
│       ├── session.py             # Session CRUD endpoints
│       ├── chat.py                # Chat endpoint
│       ├── media.py               # Frame & audio endpoints
│       ├── admin.py               # Admin/monitoring
│       ├── config.py              # Runtime config API
│       └── tts.py                 # TTS audio serving
├── providers/
│   ├── base.py                    # BaseProvider ABC
│   ├── llm/
│   │   ├── base.py                # LLMProvider ABC
│   │   ├── groq.py                # Groq LLM
│   │   └── openai.py              # OpenAI-compatible LLM
│   ├── tts/
│   │   ├── base.py                # TTSProvider ABC
│   │   ├── gemini.py              # Google Gemini TTS
│   │   └── pyttsx3.py             # Local TTS fallback
│   ├── stt/
│   │   ├── base.py                # STTProvider ABC
│   │   └── faster_whisper.py      # faster-whisper STT
│   ├── ser/
│   │   ├── base.py                # SERProvider ABC
│   │   ├── wavlm_hubert.py        # WavLM+HuBERT fusion
│   │   └── joint_ser.py           # JointSER model definition
│   ├── fer/
│   │   ├── base.py                # FERProvider ABC
│   │   ├── deepface.py            # DeepFace FER
│   │   └── deepface_worker.py     # Multi-thread worker
│   └── rag/
│       ├── base.py                # RAGProvider ABC
│       ├── chroma.py              # ChromaDB RAG
│       └── hybrid_faiss.py        # FAISS+BM25 hybrid
├── schemas/
│   ├── session.py                 # Session request/response models
│   ├── chat.py                    # Chat request/response models
│   ├── emotion.py                 # Emotion data models
│   └── admin.py                   # Admin response models
├── storage/
│   ├── base.py                    # SessionStore ABC
│   └── csv_store.py               # CSV/JSON session storage
└── utils/
    ├── audio.py                   # Audio decode/resample helpers
    └── logging.py                 # Logging configuration
```

---

## System Prompt

The system prompt (configured via `NOMEDA_LLM__SYSTEM_PROMPT`) defines the AI therapist's personality and behavior. Default:

```
You are a warm, present, deeply human therapist named Nomeda...
- Person-centered (Rogers), MI, CBT
- Warm, natural voice, open-ended questions
- Multimodal awareness (face/voice emotions used subtly)
- RAG context as optional reference (ignored if irrelevant)
- Always outputs JSON: {"response": "...", "distress": <0-100>}
- Safety protocol for crisis/suicide ideation
```

The conversation context injected before the user's message:

```
[REFERENCE CONTEXT — IGNORE IF NOT RELEVANT]
Facial emotion: sad
Voice emotion: neutral
Distress level: 60/100
Relevant context:
[CBT therapy excerpt about worry...]
```

Previous 10 exchanges are also included as `user`/`assistant` pairs for short-term memory.
