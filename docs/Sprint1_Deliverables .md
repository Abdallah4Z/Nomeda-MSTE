# Sprint 1 — Define & Architect
## NextCity AI Hackathon | May 7, 2026 | 10:00–11:00

---

## BUSINESS DELIVERABLES

### 1. Problem Statement (3 Sentences)

**Theme:** Smart Health & Well-being in Future Cities

In today's high-pressure urban environments, millions suffer from chronic stress and emotional burnout but remain entirely disconnected from professional mental health support due to cultural stigma, prohibitive costs, and severely bottlenecked healthcare systems. Traditional therapy is a luxury — expensive, slow, and intimidating — while individuals often lack the emotional vocabulary to articulate their distress, especially when speaking in local dialects. Nomeda Therapist bridges this gap with an on-demand, multimodal AI platform that analyzes facial expressions, voice tone, and biometrics in real time to deliver instant, empathetic, and clinically grounded therapeutic support — anywhere, anytime, judgment-free.

### 2. Primary User & Pain Point

| Aspect | Detail |
|--------|--------|
| **Primary Beneficiary** | Young professionals (ages 22–40) and university students in Egypt and the MENA region suffering from chronic stress, burnout, and anxiety |
| **Key Pain Point** | Therapy is inaccessible — financially (expensive), logistically (waiting lists), culturally (stigma), and emotionally (cannot articulate feelings) |
| **Current Alternatives** | Expensive private clinics, overburdened public mental health services, self-help apps (non-personalized), or silence |
| **Why They Need Us** | Immediate, affordable, private, and does not require the user to be an expert at naming their emotions — the AI reads what they cannot say |

### 3. SDG & National Smart City Alignment

| Goal | Alignment |
|------|-----------|
| **SDG 3: Good Health and Well-being** | Target 3.4 — Reduce premature mortality from non-communicable diseases by 1/3 through prevention and treatment; mental health is explicitly included |
| **SDG 10: Reduced Inequalities** | Makes mental health support affordable and accessible to lower-income populations priced out of traditional care |
| **Egypt Vision 2030 / Smart Cities** | Aligns with Egypt's health sector digitization strategy and New Alamein City's vision as a smart, inclusive urban center leveraging AI for citizen well-being |

### 4. Value Proposition

> **"Nomeda Therapist is the first AI therapist that sees how you feel, hears what you cannot say, and responds like a real clinician — in seconds, on any device, for the cost of a streaming subscription."**

| Who Benefits | How | How Much |
|-------------|-----|----------|
| **Users** (stressed professionals/students) | Immediate, private, affordable emotional support without stigma or waiting lists | ~50 EGP/month subscription vs. 300–800 EGP per private session — up to **94% cheaper** than traditional therapy |
| **Healthcare System** | Reduces burden on overstretched public mental health services | One deployment serves **~10,000 concurrent users** with zero added clinic capacity — equivalent to the throughput of **~50 full-time therapists** |
| **Employers / Universities** | Improves employee/student well-being and productivity | Workplace stress costs employers an estimated **3–4% of payroll** in lost productivity; even a 10% reduction translates to significant ROI per employee |


### What Makes Nomeda Different

Existing AI mental health apps are **text-only chatbots**. Nomeda is the first to combine:

1. **Multimodal sensing** — face + voice + biometrics fused in real time, not just text input
2. **Arabic & MENA dialect support** — built for our region, not a translated Western product
3. **Clinically grounded responses** — RAG over therapy literature, not generic chatbot replies
4. **On-device deployment option** — runs locally for full privacy, critical in stigma-heavy cultures

### Why Now?

Three forces converge in 2026 to make Nomeda possible and necessary:

1. **Open-weight LLMs are finally good enough** — Gemma 3 and similar models can run locally on consumer hardware, eliminating the $0.10+/session cost that killed earlier attempts
2. **Post-pandemic mental health awareness in MENA** — stigma is decreasing, especially among Gen Z and millennials, while clinical capacity has not kept pace with rising demand
3. **Smart city infrastructure rollout** — Egypt's Vision 2030 and New Alamein deployment create direct channels for AI-powered citizen wellness services at scale

### 5. Business Model Canvas (Key Blocks)

| Block | Description |
|-------|-------------|
| **Value Proposition** | Real-time multimodal AI therapy: face + voice + biometric analysis fused through a clinically grounded LLM, delivered via web dashboard with instant spoken response |
| **Customer Segments** | (1) B2C: Young professionals & students (direct subscription), (2) B2B: Corporate wellness programs & university counseling centers, (3) B2G: National mental health initiatives & smart city deployments |
| **Revenue Streams** | (1) Freemium SaaS (basic 3 sessions/month free, premium ~50 EGP/month), (2) B2B licensing for institutions (per-seat or per-deployment), (3) Government/non-profit grants for mental health infrastructure |
| **Key Resources** | Fine-tuned Gemma 3 LLM on therapy data, WavLM+HuBERT SER model, DeepFace/MediaPipe FER pipeline, FAISS/ChromaDB RAG, Docker deployment kit, proprietary training datasets |
| **Key Activities** | Real-time multimodal inference, LLM response generation, continuous model fine-tuning, secure session storage, platform maintenance & scaling |
| **Key Partnerships** | Universities (clinical validation studies), licensed therapists (curation of training data & response quality audit), telecom providers (distribution), NGOs (subsidized access for underserved communities) |
| **Customer Relationships** | Automated AI therapist (24/7), optional human escalation channel, periodic well-being check-ins, transparent data privacy policy |
| **Channels** | Web app (primary), mobile app (roadmap), WhatsApp bot (roadmap), institutional deployment on-premise |
| **Cost Structure** | Cloud GPU inference (~$0.002/session), model training & fine-tuning, API costs (Groq fallback, Gemini TTS), R&D salaries, marketing & distribution |

---

## TECHNICAL DELIVERABLES

### 1. GitHub Repository

- **URL:** `https://github.com/Abdallah4Z/Nomeda-MSTE`
- **Status:** ✅ Repository created, all team members invited
- **Visibility:** Public (as required by hackathon submission)
- **Structure:** Monorepo with microservice architecture, 2 commits on `main` (initial commit + hardware tests)

### 2. Tech Stack (Finalized)

| Layer | Technology | Choice Rationale |
|-------|-----------|-----------------|
| **Language** | Python 3.10+ | Ecosystem dominance for ML/CV; FastAPI async support |
| **Web Framework** | FastAPI | Async-first, WebSocket-native, auto-docs, highest performance Python API framework |
| **Face Emotion (FER)** | DeepFace + MediaPipe FaceMesh | DeepFace: 7-emotion classification; MediaPipe: 468 landmark tracking for drowsiness/yawning/head-pose |
| **Voice Emotion (SER)** | WavLM (`microsoft/wavlm-base-plus`) + HuBERT (`facebook/hubert-base-ls960`) fusion | Self-supervised transformers — state-of-the-art SER; fine-tuned on custom emotion dataset |
| **Speech-to-Text** | faster-whisper (tiny) | 10× faster than OpenAI Whisper; tiny model gives <500ms latency locally |
| **LLM** | Gemma 3 (fine-tuned, 2B GGUF) via `llama-cpp-python` | Best open-weight model for on-device inference; fine-tuned on therapy-specific dialogues |
| **LLM Fallback** | Groq API (Llama 3.3 70B) | Low-latency cloud fallback when local model unavailable |
| **RAG** | FAISS (index) + ChromaDB (persistent store) + `all-MiniLM-L6-v2` (embeddings) | FAISS for speed; ChromaDB for durability; MiniLM for lightweight embedding |
| **Text-to-Speech** | Qwen3-Audio (1.7B) / Google Gemini Flash TTS | Natural expressive speech; Arabic and dialect support |
| **TTS Fallback** | pyttsx3 | Offline-capable fallback |
| **Biometrics** | MAX30102 PPG sensor (I2C) + Arduino firmware | Heart rate & SpO2; low-cost, widely available sensor |
| **Frontend** | HTML5, CSS3, Vanilla JS + Chart.js + Three.js | Zero build step; Chart.js for real-time plots; Three.js for 3D avatar |
| **Containerization** | Docker + Docker Compose (multi-stage build) | Portable deployment; microservice or monolithic mode |
| **Infrastructure** | NVIDIA GPU / Jetson / x86 CPU | CUDA 12.2 for GPU; CPU fallback via GGUF quantization |

### 3. Datasets & APIs

| Resource | Type | Status | Purpose |
|----------|------|--------|---------|
| AffectNet | Dataset (FER) | ✅ Integrated | DeepFace backbone trained on 1M+ labeled faces |
| IEMOCAP / RAVDESS | Dataset (SER) | ✅ Fine-tuned | WavLM+HuBERT trained on 4-class emotion (happy, sad, angry, neutral) |
| DEAP / WESAD | Dataset (Biometric) | 🟡 Reference | Physiological signal benchmarks for PPG/EDA processing |
| Groq API | API | ✅ Configured | Fallback LLM (Llama 3.3 70B) when local model unavailable |
| Gemini TTS API | API | ✅ Configured | High-quality text-to-speech with emotional expression |
| FAISS + ChromaDB | Vector Store | ✅ Built | RAG over therapy literature (SDG 3 knowledge base) |
| News API | API | 🟡 Available | Optional real-time context retrieval for mental health news |

### 4. System Architecture Diagram

```
                        ┌─────────────────────────────────────────────┐
                        │              WEB BROWSER                    │
                        │  (HTML5/JS/Chart.js/Three.js Frontend)      │
                        │  Camera | Mic | Dashboard | 3D Avatar       │
                        └──────────────┬──────────────────────────────┘
                                       │ WebSocket + HTTP
                                       ▼
              ┌──────────────────────────────────────────────────┐
              │              WEB API (Port 8010)                  │
              │         FastAPI Orchestrator + Session Mgr        │
              │  ┌─────────┐ ┌──────────┐ ┌───────────┐          │
              │  │ Frames  │ │  Audio   │ │ Biometric │          │
              │  └────┬────┘ └────┬─────┘ └─────┬─────┘          │
              └───────┼───────────┼─────────────┼────────────────┘
                      │           │             │
         ┌────────────┼───────────┼─────────────┼────────────┐
         ▼            ▼           ▼             ▼             │
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
   │ FACE     │ │ VOICE    │ │ BIOMETRIC│ │ FUSION   │      │
   │ ANALYSIS │ │ ANALYSIS │ │ PROCESSOR│ │ LLM      │      │
   │ :8001    │ │ :8002    │ │ (built-in)│ │ :8003    │      │
   │          │ │          │ │          │ │          │      │
   │ DeepFace │ │ Whisper  │ │ MAX30102 │ │ Gemma 3  │      │
   │ MediaPipe│ │ WavLM+   │ │ I2C      │ │ GGUF     │      │
   │          │ │ HuBERT   │ │ Arduino  │ │ FAISS    │      │
   └──────────┘ └──────────┘ └──────────┘ │ RAG      │      │
                                          │ Gemini   │      │
                                          │ TTS      │      │
                                          └──────────┘      │
                                                   ┌─────────┴──────┐
                                                   │ Session Logger │
                                                   │   (CSV / API)   │
                                                   └────────────────┘
```

**Data Flow:**
1. Browser streams camera + mic via WebSocket to Web API
2. Web API dispatches frames to Face Analysis (port 8001) and audio chunks to Voice Analysis (port 8002)
3. Face Analysis returns emotion label + confidence + face landmarks
4. Voice Analysis returns emotion label + transcription (STT)
5. Biometric Processor reads heart rate/SpO2 from MAX30102 or mock
6. Fusion LLM (port 8003) receives all 3 modalities + transcribed text
7. Fusion LLM queries FAISS RAG for relevant therapy knowledge
8. LLM generates distress score + therapist response text
9. Response is converted to speech via TTS and streamed back to browser
10. All data logged to session CSV

### 5. MVP Scope Definition

**MVP = Minimum Viable Presentation for Demo**

The system is already ~95% complete. For the hackathon demo, the MVP is:

| Component | In MVP? | Status | Notes |
|-----------|---------|--------|-------|
| Face Emotion Detection | ✅ YES | Complete | DeepFace + MediaPipe; 7 emotions + drowsiness |
| Voice Emotion Recognition | ✅ YES | Complete | WavLM+HuBERT fusion; 4 emotions |
| Speech-to-Text | ✅ YES | Complete | faster-whisper tiny |
| LLM Therapist Response | ✅ YES | Complete | Gemma 3 GGUF local + Groq fallback |
| Text-to-Speech | ✅ YES | Complete | Gemini TTS + pyttsx3 fallback |
| Web Dashboard (Live Mode) | ✅ YES | Complete | Camera, metrics, distress gauge, chat |
| Session Logging | ✅ YES | Complete | CSV logger |
| Biometric (MAX30102) | ⚠️ OPTIONAL | Complete but HW-dependent | Mock mode available for demo |
| Video Session Analysis | ✅ YES | Complete | Upload/record + timeline |
| 3D Avatar Mode | 🟡 STRETCH | Complete | Three.js mirroring emotion |
| RAG Integration | ✅ YES | Complete | FAISS + ChromaDB grounding LLM responses in therapy literature |
| Docker Deployment | ✅ YES | Complete | Microservice + monolithic both ready |

**Demo Flow (5 min):**
1. Open web dashboard → Live Monitoring tab
2. Turn on camera → real-time face emotion displayed
3. Speak into mic → STT transcribes, SER detects vocal emotion
4. Dashboard shows fused distress score (0–100) with gauge
5. AI therapist responds via chat bubble + spoken TTS
6. Stress scenario: show the system detecting distress and responding empathetically

---

## CHECKLIST

### Business ✅
- [x] 3-sentence problem statement
- [x] Primary user & pain point defined
- [x] SDG 3 + Egypt Vision 2030 alignment
- [x] Value proposition drafted
- [x] Business model canvas (5 key blocks)

### Technical ✅
- [x] GitHub repo set up (https://github.com/Abdallah4Z/Nomeda-MSTE)
- [x] Tech stack finalized and documented
- [x] Datasets/APIs identified and tested
- [x] System architecture diagram drawn
- [x] MVP scope defined (demo-ready)
