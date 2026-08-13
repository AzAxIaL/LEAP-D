# LEAP-D: Longitudinal ESL Assessment of Proficiency and Disfluency

**Local-first, privacy-preserving speech analysis for adult Japanese EFL contexts.**

Version: 0.1.0 | Phase: 1 (MVP) | Status: Development

LEAP-D is a local-first web application for longitudinal, evidence-linked formative assessment of spoken English in adult Japanese EFL contexts. It provides trusted multi-track review, reliable transcript correction, teacher-controlled disfluency analysis, and CEFR-aligned evidence profiles—without requiring cloud processing or compromising learner dignity.

## Principles

1. **Privacy-first local processing** — Audio stays on-device by default; cloud features are opt-in
2. **Teacher-in-the-loop** — All automated analyses require human review before high-stakes use
3. **Evidence-linked assessments** — Every claim links to timestamped audio, transcript, and provenance
4. **Fairness and dignity** — Japanese use and L2 phenomena are not treated as errors
5. **No medical diagnosis** — Disfluency patterns are never labeled as speech disorders
6. **Learner dignity** — Preserve translanguaging verbatim; separate L2 planning from disorder-like patterns

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2, Alembic
- **Frontend**: React + TypeScript + Vite
- **Database**: SQLite (default), PostgreSQL (optional)
- **Audio Processing**: FFmpeg, Whisper/faster-whisper/WhisperX, pyannote (Phase 2)
- **AI**: Ollama/local LLMs (default), optional cloud adapters

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- FFmpeg (`choco install ffmpeg` on Windows)
- GPU drivers (optional, for accelerated ASR)

### Setup

```powershell
# Backend setup
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head

# Frontend setup
cd ../frontend
npm install
npm run dev
```

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
DATABASE_URL=sqlite:///./data/efl_analysis.db
ASR_PROVIDER=whisper
DIARIZATION_PROVIDER=pyannote
LLM_PROVIDER=ollama
GPU_ENABLED=false
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/          # REST endpoints
│   │   ├── core/         # Config, security
│   │   ├── db/           # Database session, base
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   ├── jobs/         # Background job orchestration
│   │   ├── providers/    # ASR, diarization, LLM interfaces
│   │   └── utils/        # Helpers
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   ├── pages/        # Route pages
│   │   ├── hooks/        # Custom React hooks
│   │   ├── store/        # State management
│   │   ├── types/        # TypeScript types
│   │   └── utils/        # Helpers
│   └── public/
├── data/                   # Application-managed storage
├── scripts/                # PowerShell setup/run scripts
└── fixtures/               # Test fixtures, sample manifests
```

## Phased Delivery

### Phase 1 (MVP) — Trusted Multi-Track Review
- Course/student/session management
- Multi-track audio import and preprocessing
- Configurable ASR with word timestamps
- Transcript review and correction
- Disfluency detection (rule/timing-based)
- Fluency metrics and formative reports

### Phase 2 — Mixed-Audio Identity
- Speaker diarization (pyannote)
- Voiceprint enrollment and matching
- One-to-one identity assignment with confidence thresholds

### Phase 3 — Advanced Pedagogical Analysis
- Pronunciation observations (explainable, reviewable)
- CEFR/ACTFL evidence profiles
- Interactional comprehension analysis
- Mediation and plurilingual behaviour tracking

## Assessment Framework

### CEFR Companion Volume Alignment
- Spoken production & interaction
- Phonological control (range, accuracy, fluency, prosody)
- Online conversation/discussion
- Mediation (text, concepts, communication)
- Plurilingual/pluricultural competence

### ACTFL Crosswalk
- Optional indicative mapping (not one-to-one conversion)
- Stored separately from CEFR evidence

## Privacy & Consent

- First names only; no video or email ingestion
- Explicit consent required for voiceprints (revocable)
- Raw audio never leaves device unless cloud feature enabled
- Cascading deletion with audit trail
- Configurable retention policies

## Quality Assurance

- ASR WER tracking
- Diarization DER monitoring
- Disfluency precision/recall by category
- Human-rating agreement studies
- Teacher override rate tracking

## License

[Specify license]

## Validation Status

⚠️ This system requires validation against independent teacher-rated data representative of adult Japanese EFL learners before claims of validity can be made.
