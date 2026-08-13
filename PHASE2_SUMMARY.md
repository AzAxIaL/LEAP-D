# Phase 2 Implementation Summary: Mixed-Audio Identity

## Overview
Phase 2 adds speaker diarization and voiceprint-based identity matching for mixed audio files, enabling LEAP-D to process single-recordings of multi-speaker classroom interactions.

## Completed Components

### 1. Diarization Service (`backend/app/services/diarization.py`)
**Provider Interface:**
- `DiarizationProvider` abstract base class
- `PyAnnoteDiarizationProvider`: Production implementation using pyannote.audio 3.1
- `MockDiarizationProvider`: Testing fallback

**Features:**
- Lazy model loading for memory management
- GPU/CPU automatic fallback
- Speaker turn extraction with timestamps
- Overlap detection support
- Configurable speaker count hints

**Configuration:**
```env
DIARIZATION_PROVIDER=pyannote  # or "mock"
HUGGINGFACE_TOKEN=your_token   # Required for pyannote gated models
```

### 2. Voiceprint Service (`backend/app/services/voiceprint.py`)
**Core Classes:**
- `VoiceprintEmbedding`: Dataclass for stored embeddings
- `SpeakerMatch`: Matching result with confidence scores
- `VoiceprintProvider`: Abstract interface
- `PyannoteEmbeddingProvider`: Production embedding extractor
- `VoiceprintService`: Enrollment, matching, deletion

**Key Features:**
- **Consent-gated enrollment**: Requires valid consent record
- **Duration validation**: 30-90 second enrollment audio
- **Quality scoring**: SNR and variance-based quality metrics
- **Cosine similarity matching**: One-to-one assignment constraint
- **Confidence thresholds**: Configurable match/enroll thresholds
- **Alternative matches**: Top-3 candidate preservation
- **Deletion workflow**: Consent withdrawal support

**Security:**
- Embeddings never leave the device (unless cloud explicitly enabled)
- First-name only storage
- Revocable consent with cascading deletion

### 3. Identity Resolution Service (`backend/app/services/identity_resolution.py`)
**Multi-Source Fusion:**
Priority order for identity assignment:
1. **Manual** (teacher override) - highest priority
2. **Track assignment** (multi-track mode)
3. **Voiceprint match** (with confidence threshold)
4. **Diarization-only** (unknown labels preserved)

**Safeguards:**
- One-to-one student assignment constraint
- Unknown label preservation (`DIAR_*`, `UNKNOWN`)
- Confidence-weighted resolution
- Review queue flagging (low-confidence matches)
- Audit trail for all assignments

**Output:**
- `IdentityResolutionResult`: Complete resolution with metadata
- `IdentityAssignment`: Per-segment assignment with provenance
- Confidence summary statistics

### 4. API Routes (`backend/app/routers/diarization.py`)
**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/diarization/process` | Run diarization on mixed audio |
| POST | `/api/v1/diarization/voiceprint/enroll` | Enroll student voiceprint |
| POST | `/api/v1/diarization/voiceprint/match` | Match voiceprints to segments |
| POST | `/api/v1/diarization/identity/resolve` | Resolve final identities |
| GET | `/api/v1/diarization/voiceprints/list` | List enrolled voiceprints |
| DELETE | `/api/v1/diarization/voiceprint/{id}` | Delete voiceprint (consent withdrawal) |

**Request/Response Schemas** (`backend/app/schemas/diarization.py`):
- `DiarizationRequest/Response`
- `SpeakerTurnSchema`
- `VoiceprintEnrollRequest`
- `VoiceprintMatchRequest`
- `IdentityAssignmentSchema`
- `IdentityResolutionResponse`

### 5. Integration
- Registered in `backend/app/main.py` under `/api/v1/diarization` prefix
- 38 total routes now available
- All services import successfully

## Usage Workflow

### Step 1: Enroll Voiceprints (Requires Consent)
```bash
curl -X POST http://localhost:8000/api/v1/diarization/voiceprint/enroll \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": 1,
    "audio_file_id": 5,
    "consent_record_id": 3
  }'
```

### Step 2: Process Diarization
```bash
curl -X POST http://localhost:8000/api/v1/diarization/process \
  -H "Content-Type: application/json" \
  -d '{
    "audio_file_id": 1,
    "num_speakers_hint": 4
  }'
```

### Step 3: Match Voiceprints
```bash
curl -X POST http://localhost:8000/api/v1/diarization/voiceprint/match \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 1,
    "audio_file_id": 1,
    "match_threshold": 0.65
  }'
```

### Step 4: Resolve Identities
```bash
curl -X POST http://localhost:8000/api/v1/diarization/identity/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 1,
    "audio_file_id": 1,
    "student_names": {"1": "Yuki", "2": "Kenji"},
    "match_threshold": 0.65
  }'
```

## Privacy & Compliance

### Consent Requirements
- Voiceprint enrollment requires active `Consent` record
- Consent type: `"voiceprint"`
- Withdrawal triggers immediate deletion workflow

### Data Minimization
- First names only (no last names, emails)
- No raw audio in exports
- No biometric data in reports
- Embeddings stored locally by default

### Deletion Workflow
```python
# Consent withdrawal
DELETE /api/v1/diarization/voiceprint/{student_id}
→ Removes embedding from memory
→ Marks for database deletion
→ Cascades to dependent artifacts
```

## Model Dependencies

### PyAnnote Audio
```bash
pip install pyannote.audio==3.1.1
```

**Gated Models (require HuggingFace token):**
- `pyannote/speaker-diarization-3.1` (diarization)
- `pyannote/embedding` (voiceprints)

**Obtain Token:**
1. Create HuggingFace account
2. Accept model licenses at:
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/embedding
3. Generate token at https://huggingface.co/settings/tokens
4. Set `HUGGINGFACE_TOKEN` in `.env`

### CPU/GPU Memory Management
- Models loaded lazily (on first use)
- Sequential processing (no simultaneous ASR + diarization + LLM)
- Automatic CPU fallback if GPU unavailable
- Explicit memory release between stages

## Testing Without Hardware

### Mock Providers
Both diarization and voiceprint services include mock providers for testing:

```python
from app.services.diarization import get_diarization_provider
from app.services.voiceprint import get_voiceprint_service

# Uses mock provider when no HF token
diarizer = get_diarization_provider("mock")
voiceprint_svc = get_voiceprint_service("mock")

# Generates synthetic turns/embeddings
turns = diarizer.process(audio_path)
matches = voiceprint_svc.match_speakers(...)
```

## Next Steps for Full Phase 2

1. **Database Integration**
   - Store `VoiceprintEmbedding` in database (currently in-memory)
   - Persist `IdentityResolutionResult` for audit trail
   - Add migration for new tables

2. **Frontend UI**
   - Voiceprint enrollment page with audio preview
   - Diarization visualization (speaker timeline)
   - Identity correction interface
   - Consent management dashboard

3. **Job Orchestration Integration**
   - Add `DIARIZATION` and `IDENTITY` stages to job pipeline
   - Progress tracking for long-running diarization
   - Retry logic for failed matching

4. **Testing**
   - Unit tests for cosine similarity matching
   - Integration tests with real audio files
   - Accuracy benchmarks against labeled datasets

5. **Documentation**
   - User guide for voiceprint enrollment
   - Teacher workflow for identity correction
   - Privacy policy updates for biometric data

## Acceptance Criteria Met

✅ Diarization provider interface with pyannote support  
✅ Voiceprint enrollment with consent verification  
✅ Cosine similarity matching with one-to-one constraint  
✅ Multi-source identity fusion (manual, track, voiceprint, diarization)  
✅ Unknown label preservation (DIAR_*, UNKNOWN)  
✅ Confidence thresholds and review flags  
✅ Deletion workflow for consent withdrawal  
✅ API endpoints for all operations  
✅ Mock providers for testing  
✅ Memory-safe sequential processing  

## Remaining Phase 2 Tasks

⏳ Database persistence for voiceprints  
⏳ Frontend voiceprint enrollment UI  
⏳ Job stage integration  
⏳ Comprehensive test suite  
⏳ Validation against labeled datasets  

---

**Status**: Phase 2 backend services complete (~60%). Frontend integration and database persistence remaining.
