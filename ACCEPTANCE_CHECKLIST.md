# LEAP-D Acceptance Checklist

This document maps specification requirements to implementation verification.

## 1. Core Architecture

### Backend
- [ ] Python 3.11+ with FastAPI, Pydantic v2, SQLAlchemy 2
- [ ] Alembic migrations configured and tested
- [ ] SQLite default, PostgreSQL optional via configuration
- [ ] Background job manager with persistent state, logs, cancellation, retry
- [ ] Service boundaries: ingest, preprocess, asr, alignment, diarization, identity, transcript, disfluency, fluency_metrics, pronunciation, interaction, assessment, reports, privacy, export
- [ ] Typed provider interfaces; no assessment logic in routers
- [ ] REST API plus SSE/WebSocket for progress

### Frontend
- [ ] React + TypeScript + Vite (not Svelte)
- [ ] Accessible component system
- [ ] Keyboard-first review tools
- [ ] Responsive layout
- [ ] Single cohesive GUI

### Storage
- [ ] `data/audio/{course_id}/{session_id}/original/`
- [ ] `data/processed/{course_id}/{session_id}/`
- [ ] `data/voiceprints/{student_id}/`
- [ ] `data/artifacts/{session_id}/{job_id}/`
- [ ] `data/reports/{course_id}/{student_id_or_course_id}/`
- [ ] Content hash, original filename, codec/duration metadata tracked
- [ ] No silent rename/delete of originals

## 2. Phase 1 MVP Features

### Course/Student Management
- [ ] Create course with retention policy
- [ ] Add students with stable IDs and first names only
- [ ] Consent state tracking per feature
- [ ] CSV import for students

### Session Management
- [ ] Create session linked to course
- [ ] Multi-track file import
- [ ] Single mixed-file import
- [ ] Role assignment (student/instructor/unknown/mixed)
- [ ] Manifest preview before processing

### Audio Processing
- [ ] FFmpeg validation and preprocessing
- [ ] Configurable ASR provider selection
- [ ] Word timestamps extraction
- [ ] Segment confidence capture
- [ ] Model/version metadata storage
- [ ] CPU fallback when GPU unavailable

### Transcript Review
- [ ] Waveform rendering with multi-track support
- [ ] Speaker-coloured utterance regions
- [ ] Click-to-seek playback
- [ ] Transcript editing with provenance
- [ ] Speaker assignment correction
- [ ] Split/merge utterances
- [ ] Correction creates immutable revision

### Disfluency Detection
- [ ] Rule-based candidate detection
- [ ] Timing/VAD signal analysis
- [ ] Candidate taxonomy (filled pause, repetition, false start, repair, etc.)
- [ ] Accept/reject workflow
- [ ] Statuses: pending, accepted, rejected, needs_context
- [ ] Rejected candidates excluded from metrics

### Fluency Metrics
- [ ] Total words, utterances, speaking time
- [ ] Speech rate and articulation rate (with eligibility flags)
- [ ] Pause duration/rate distribution
- [ ] Disfluency rates (reviewed only)
- [ ] Mean utterance length
- [ ] Lexical diversity with minimum-sample warnings
- [ ] Denominator definitions documented

### Reports
- [ ] Session formative report
- [ ] Student course progress report
- [ ] Evidence-linked output
- [ ] HTML, JSON, CSV, PDF export formats
- [ ] Versioned with rationale and rubric version

## 3. Privacy & Consent

- [ ] First names only in database
- [ ] No video or email address ingestion
- [ ] Consent recorded before voiceprint enrollment
- [ ] Consent withdrawal workflow
- [ ] Cascading deletion preview
- [ ] Voiceprint deletion removes embedding and matching history
- [ ] Raw audio never leaves computer by default
- [ ] Cloud features disabled by default
- [ ] Cloud usage shows provider, data categories, anonymization status
- [ ] API keys in environment variables only (not in database/logs)

## 4. CEFR Assessment Framework

### Primary Framework Implementation
- [ ] Spoken production descriptors
- [ ] Spoken interaction descriptors
- [ ] Qualitative aspects (range, accuracy, fluency, interaction, coherence)
- [ ] Phonological control (overall, articulation, prosodic features)
- [ ] Online conversation/descriptors when evidenced
- [ ] Mediation descriptors
- [ ] Plurilingual behaviour as observation not error

### Output Policy
- [ ] Evidence profile by construct
- [ ] Provisional CEFR range (not single level)
- [ ] Confidence and coverage indicators
- [ ] Descriptor IDs/text with timestamped examples
- [ ] Counter-evidence display
- [ ] Instructor-confirmed level separate from automated estimate
- [ ] Rationale, rubric version, model versions, review timestamp
- [ ] `INSUFFICIENT EVIDENCE` when thresholds not met

### ACTFL Crosswalk
- [ ] Stored separately from CEFR evidence
- [ ] Labelled as indicative only
- [ ] No claim of one-to-one conversion

## 5. Scope Limitations Enforced

- [ ] No global listening score from classroom audio
- [ ] No reading/writing proficiency claims
- [ ] Interactional-response labelled as observed behaviour, not listening comprehension
- [ ] Japanese/code-switching preserved verbatim, not treated as errors
- [ ] No diagnostic claims about stuttering or speech disorders
- [ ] Common L2 planning phenomena separate from disorder-like patterns

## 6. Audio/ASR/Model Management

### Preprocessing
- [ ] FFmpeg validates inputs
- [ ] Extracts audio to configurable format (default 16 kHz mono WAV)
- [ ] Optional loudness normalization
- [ ] Optional silence trimming with timing map
- [ ] Corrupt/missing file detection with actionable errors

### ASR Provider Interface
- [ ] Whisper family support
- [ ] faster-whisper support
- [ ] WhisperX support (when alignment dependencies available)
- [ ] crisperwhisper support
- [ ] Language configuration
- [ ] Word timestamps where supported
- [ ] Segment confidence
- [ ] Model/version metadata
- [ ] CPU fallback
- [ ] Chunking for sessions up to 2 hours with overlap

### GPU/RAM Policy
- [ ] Heavy stages processed sequentially
- [ ] Models not loaded simultaneously without memory budget check
- [ ] GPU memory released between stages
- [ ] Subprocess resources cleaned up
- [ ] Actual provider/device/model settings logged
- [ ] Safe CPU fallback
- [ ] Smaller model choices available
- [ ] Disk space checks
- [ ] Resumable artifacts
- [ ] Lazy UI loading
- [ ] Paginated transcripts
- [ ] Out-of-memory guidance (no crash)

## 7. Diarization & Identity (Phase 2)

- [ ] pyannote-based diarization behind provider interface
- [ ] VAD and speaker turn segmentation
- [ ] Embedding extraction for clean segments only
- [ ] Consented voiceprint matching
- [ ] Cosine similarity with quality-aware aggregation
- [ ] Configurable assign/suggest thresholds
- [ ] One-to-one matching constraint by default
- [ ] Low-confidence labels remain `DIAR_*` or `UNKNOWN`
- [ ] Suggestions shown, never forced identities
- [ ] Assignment source tracked (manual, track, voiceprint, diarization, import)
- [ ] Confidence stored

## 8. LLM Guardrails

- [ ] Ollama/local models by default
- [ ] Cloud LLM adapters disabled by default
- [ ] LLM input minimal, structured, provenance-labelled
- [ ] LLM outputs validate against strict JSON Schema
- [ ] Evidence IDs, uncertainty, model/prompt version included
- [ ] LLMs cannot fabricate quotations/timestamps
- [ ] LLMs cannot infer stable traits
- [ ] LLMs cannot diagnose conditions
- [ ] LLMs cannot override teacher decisions
- [ ] LLMs cannot issue standalone certified levels
- [ ] LLM jobs run after ASR/diarization resources unload

## 9. GUI Pages

- [ ] Dashboard — courses, pending reviews, jobs, warnings, recent reports
- [ ] Courses — course lifecycle, sessions, analytics
- [ ] Students — stable ID, first name, consent/retention, profile, voiceprint state, CSV import
- [ ] Import Center — drag/drop, folders, file inspection, role assignment, manifest preview
- [ ] Sessions — files, processing, metrics, analyses, revisions
- [ ] Voiceprints — enrollment, quality, consent, source, re-enrollment, deletion
- [ ] Jobs — queued/running/failed/completed, stage, logs, cancel/retry
- [ ] Session Review — primary workspace with waveform, transcript, speakers, events
- [ ] Progress — student/course trends with uncertainty and export
- [ ] Reports — create, preview, version, export
- [ ] Settings — providers, models, thresholds, storage, privacy, cloud toggles

### Session Review Workspace
- [ ] Waveform rendering
- [ ] Multi-track selection
- [ ] Speaker-coloured utterance regions
- [ ] Event markers
- [ ] Play/pause/seek/zoom controls
- [ ] Transcript and word sync
- [ ] Click-to-seek
- [ ] Transcript/speaker edits
- [ ] Split/merge functionality
- [ ] Boundary adjustment where reliable
- [ ] Correction provenance display
- [ ] Review queues
- [ ] Bulk actions
- [ ] Filters and saved filters
- [ ] Keyboard shortcuts (Space, arrows, S, M, up/down, A, R, Z, X)
- [ ] Shortcuts discoverable and avoid conflicts while typing
- [ ] Side panels for evidence profile, pronunciation, interaction, reports

## 10. Quality & Validation

### Testing
- [ ] Backend unit tests
- [ ] API integration tests
- [ ] Frontend component tests
- [ ] E2E tests where practical
- [ ] Fixture generator
- [ ] Sample manifests
- [ ] Synthetic/sample audio guidance (respects licensing)

### Research/Validation Metrics (Tracked Separately)
- [ ] ASR WER measurement capability
- [ ] Diarization DER measurement capability
- [ ] Speaker-ID accuracy tracking
- [ ] Disfluency precision/recall by category
- [ ] Human-rating agreement tracking
- [ ] CEFR-range agreement tracking
- [ ] Calibration curves
- [ ] Subgroup error analysis
- [ ] Teacher override rates

## 11. Deliverables

- [ ] Backend source code
- [ ] Frontend source code
- [ ] Database models
- [ ] Alembic migrations
- [ ] One interactive web GUI (React, not Svelte)
- [ ] Local pipeline with selectable ASR, diarization, identity, LLM providers
- [ ] Configuration files
- [ ] `.env.example`
- [ ] Windows PowerShell setup/run scripts
- [ ] Test suite
- [ ] Fixtures/fixture generator
- [ ] Sample session manifest
- [ ] README with prerequisites, model licensing, GPU/CPU modes, privacy, retention, backups, troubleshooting, limits
- [ ] Assessment rubric schemas with source/version attribution
- [ ] Descriptor data with source/version attribution
- [ ] Final acceptance checklist (this document)

## 12. Documentation

- [ ] README covers installation steps
- [ ] README covers configuration options
- [ ] README covers ASR provider selection
- [ ] README covers model licensing/gated access notes
- [ ] README covers GPU/CPU mode switching
- [ ] README covers privacy/consent workflows
- [ ] README covers retention policies
- [ ] README covers backup procedures
- [ ] README covers troubleshooting common issues
- [ ] README documents limitations clearly
- [ ] README states validation status appropriately

## Sign-off

**Implementation verified against specification:** [ ]

**Date:** _______________

**Verifier:** _______________

**Notes:**

---

*Note: This checklist should be completed incrementally during development, with final sign-off after all Phase 1 MVP features are implemented, tested, and documented.*
