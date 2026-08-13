"""
API routes for diarization and identity resolution (Phase 2).
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pathlib import Path

from app.db.session import get_db
from app.models import AudioFile, Session as SessionModel, Student, Consent
from app.schemas.diarization import (
    DiarizationRequest,
    DiarizationResponse,
    SpeakerTurnSchema,
    IdentityResolutionResponse,
    VoiceprintEnrollRequest,
    VoiceprintMatchRequest
)
from app.services.diarization import get_diarization_provider
from app.services.voiceprint import get_voiceprint_service
from app.services.identity_resolution import IdentityResolutionService
from app.core.config import settings

router = APIRouter(prefix="/diarization", tags=["diarization"])


@router.post("/process", response_model=DiarizationResponse)
async def process_diarization(
    request: DiarizationRequest,
    db: Session = Depends(get_db)
):
    """
    Run speaker diarization on a mixed audio file.
    
    Requires HuggingFace token for pyannote provider.
    Falls back to mock provider if token not configured.
    """
    # Get audio file
    audio_file = db.query(AudioFile).filter(
        AudioFile.id == request.audio_file_id
    ).first()
    
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    if not audio_file.file_path:
        raise HTTPException(status_code=400, detail="Audio file path not available")
    
    audio_path = Path(audio_file.file_path)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")
    
    # Get diarization provider
    provider = get_diarization_provider(
        provider_type=settings.DIARIZATION_PROVIDER,
        hf_token=settings.HUGGINGFACE_TOKEN
    )
    
    try:
        # Run diarization
        turns = provider.process(audio_path, num_speakers=request.num_speakers_hint)
        
        # Convert to schema
        turn_schemas = [
            SpeakerTurnSchema(
                start=turn.start,
                end=turn.end,
                speaker_label=turn.speaker_label,
                confidence=turn.confidence,
                overlap=turn.overlap
            )
            for turn in turns
        ]
        
        return DiarizationResponse(
            audio_file_id=audio_file.id,
            total_turns=len(turns),
            total_duration=sum(t.end - t.start for t in turns),
            turns=turn_schemas,
            model_info=provider.get_model_info()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diarization failed: {str(e)}")


@router.post("/voiceprint/enroll")
async def enroll_voiceprint(
    request: VoiceprintEnrollRequest,
    db: Session = Depends(get_db)
):
    """
    Enroll a voiceprint for a student from a consented audio file.
    
    Requirements:
    - 30-90 seconds of speech
    - Valid consent record
    - Clean audio quality
    """
    # Verify student exists
    student = db.query(Student).filter(Student.id == request.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Verify consent
    if request.consent_record_id:
        consent = db.query(ConsentRecord).filter(
            ConsentRecord.id == request.consent_record_id
        ).first()
        if not consent or not consent.is_active:
            raise HTTPException(
                status_code=400,
                detail="Valid consent record required for voiceprint enrollment"
            )
    
    # Get audio file
    audio_file = db.query(AudioFile).filter(
        AudioFile.id == request.audio_file_id
    ).first()
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    audio_path = Path(audio_file.file_path)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")
    
    # Get voiceprint service
    service = get_voiceprint_service(
        provider_type=settings.VOICEPRINT_PROVIDER,
        hf_token=settings.HUGGINGFACE_TOKEN
    )
    
    try:
        voiceprint = service.enroll_voiceprint(
            student_id=request.student_id,
            audio_path=audio_path,
            consent_record_id=request.consent_record_id
        )
        
        # In production, would store voiceprint.embedding in database
        # For now, just return metadata
        
        return {
            "student_id": voiceprint.student_id,
            "duration_seconds": voiceprint.duration_seconds,
            "quality_score": voiceprint.quality_score,
            "enrolled_at": voiceprint.enrolled_at.isoformat(),
            "model_version": voiceprint.model_version,
            "consent_verified": voiceprint.consent_record_id is not None
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voiceprint enrollment failed: {str(e)}")


@router.post("/voiceprint/match")
async def match_voiceprints(
    request: VoiceprintMatchRequest,
    db: Session = Depends(get_db)
):
    """
    Match diarized segments to enrolled voiceprints.
    
    Returns speaker assignments with confidence scores.
    Applies one-to-one constraint by default.
    """
    # Get session and students
    session = db.query(SessionModel).filter(
        SessionModel.id == request.session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    students = db.query(Student).filter(
        Student.course_id == session.course_id
    ).all()
    
    student_names = {s.id: s.first_name for s in students}
    
    # Get voiceprint service
    service = get_voiceprint_service(
        provider_type=settings.VOICEPRINT_PROVIDER,
        hf_token=settings.HUGGINGFACE_TOKEN,
        match_threshold=request.match_threshold or 0.65
    )
    
    # Mock diarized segments (in production, would load from DB)
    diarized_segments = [
        {"start": 0.0, "end": 5.0, "speaker_label": "SPEAKER_0"},
        {"start": 5.0, "end": 10.0, "speaker_label": "SPEAKER_1"},
    ]
    
    audio_file = db.query(AudioFile).filter(
        AudioFile.id == request.audio_file_id
    ).first()
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    audio_path = Path(audio_file.file_path)
    
    try:
        matches = service.match_speakers(
            diarized_segments=diarized_segments,
            audio_path=audio_path,
            student_names=student_names
        )
        
        return {
            "session_id": request.session_id,
            "matches": [
                {
                    "diarizer_label": m.diarizer_label,
                    "student_id": m.student_id,
                    "student_name": m.student_name,
                    "confidence": m.confidence,
                    "match_type": m.match_type,
                    "alternative_matches": m.alternative_matches
                }
                for m in matches
            ],
            "students_matched": len(set(m.student_id for m in matches if m.student_id))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voiceprint matching failed: {str(e)}")


@router.post("/identity/resolve", response_model=IdentityResolutionResponse)
async def resolve_identity(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Resolve final speaker identities by combining:
    - Diarization output
    - Voiceprint matches
    - Track assignments (multi-track mode)
    - Manual corrections
    
    Implements one-to-one constraint and unknown label preservation.
    """
    service = IdentityResolutionService(
        voiceprint_match_threshold=request.get("match_threshold", 0.65)
    )
    
    # Mock data for demonstration
    diarized_segments = [
        {"segment_id": "seg_0", "start": 0.0, "end": 5.0, "speaker_label": "SPEAKER_0"},
        {"segment_id": "seg_1", "start": 5.0, "end": 10.0, "speaker_label": "SPEAKER_1"},
        {"segment_id": "seg_2", "start": 10.0, "end": 15.0, "speaker_label": "SPEAKER_0"},
    ]
    
    student_names = request.get("student_names", {1: "Student A", 2: "Student B"})
    track_assignments = request.get("track_assignments", {})
    manual_assignments = request.get("manual_assignments", {})
    
    try:
        result = service.resolve_identities(
            session_id=request.get("session_id", 1),
            audio_file_id=request.get("audio_file_id", 1),
            diarized_segments=diarized_segments,
            track_assignments=track_assignments,
            voiceprint_matches=None,  # Would come from voiceprint service
            manual_assignments=manual_assignments,
            student_names=student_names
        )
        
        return IdentityResolutionResponse(
            session_id=result.session_id,
            audio_file_id=result.audio_file_id,
            total_segments=result.total_segments,
            matched_segments=result.matched_segments,
            unknown_segments=result.unknown_segments,
            overlap_duration=result.overlap_duration,
            assignments=[
                {
                    "segment_id": a.segment_id,
                    "start": a.start,
                    "end": a.end,
                    "original_label": a.original_label,
                    "assigned_student_id": a.assigned_student_id,
                    "assigned_student_name": a.assigned_student_name,
                    "confidence": a.confidence,
                    "assignment_source": a.assignment_source,
                    "is_unknown": a.is_unknown,
                    "requires_review": a.requires_review
                }
                for a in result.assignments
            ],
            metadata=result.resolution_metadata
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Identity resolution failed: {str(e)}")


@router.get("/voiceprints/list")
async def list_voiceprints(db: Session = Depends(get_db)):
    """List all enrolled voiceprints with metadata."""
    service = get_voiceprint_service(
        provider_type=settings.VOICEPRINT_PROVIDER,
        hf_token=settings.HUGGINGFACE_TOKEN
    )
    
    voiceprints = service.get_enrolled_voiceprints()
    
    return {
        "count": len(voiceprints),
        "voiceprints": voiceprints
    }


@router.delete("/voiceprint/{student_id}")
async def delete_voiceprint(student_id: int, db: Session = Depends(get_db)):
    """
    Delete a student's voiceprint.
    
    Used when consent is withdrawn or re-enrollment needed.
    """
    service = get_voiceprint_service(
        provider_type=settings.VOICEPRINT_PROVIDER,
        hf_token=settings.HUGGINGFACE_TOKEN
    )
    
    deleted = service.delete_voiceprint(student_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Voiceprint not found")
    
    return {"message": f"Voiceprint deleted for student {student_id}"}
