"""
Pydantic schemas for diarization and identity resolution (Phase 2).
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class SpeakerTurnSchema(BaseModel):
    """Single speaker turn from diarization."""
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    speaker_label: str = Field(..., description="Speaker label (e.g., SPEAKER_0)")
    confidence: float = Field(default=0.85, description="Confidence score")
    overlap: bool = Field(default=False, description="Whether this segment overlaps with another speaker")
    track_id: Optional[str] = Field(None, description="Track ID for multi-track files")


class DiarizationRequest(BaseModel):
    """Request to run diarization on an audio file."""
    audio_file_id: int
    num_speakers_hint: Optional[int] = Field(None, description="Hint for number of speakers")
    provider: Optional[str] = Field("pyannote", description="Diarization provider")


class DiarizationResponse(BaseModel):
    """Response from diarization processing."""
    audio_file_id: int
    total_turns: int
    total_duration: float
    turns: List[SpeakerTurnSchema]
    model_info: Dict[str, Any]
    processed_at: datetime = Field(default_factory=datetime.utcnow)


class VoiceprintEnrollRequest(BaseModel):
    """Request to enroll a voiceprint."""
    student_id: int
    audio_file_id: int
    consent_record_id: Optional[int] = None


class VoiceprintMatchRequest(BaseModel):
    """Request to match voiceprints to diarized segments."""
    session_id: int
    audio_file_id: int
    match_threshold: Optional[float] = Field(0.65, ge=0.0, le=1.0)


class IdentityAssignmentSchema(BaseModel):
    """Resolved identity assignment for a segment."""
    segment_id: str
    start: float
    end: float
    original_label: str
    assigned_student_id: Optional[int]
    assigned_student_name: Optional[str]
    confidence: float
    assignment_source: str  # "track", "voiceprint", "manual", "diarization"
    is_unknown: bool
    requires_review: bool


class IdentityResolutionResponse(BaseModel):
    """Response from identity resolution."""
    session_id: int
    audio_file_id: int
    total_segments: int
    matched_segments: int
    unknown_segments: int
    overlap_duration: float
    assignments: List[IdentityAssignmentSchema]
    metadata: Dict[str, Any]


class VoiceprintInfo(BaseModel):
    """Information about an enrolled voiceprint."""
    student_id: int
    duration_seconds: float
    quality_score: float
    enrolled_at: str
    model_version: str
    has_consent: bool


class VoiceprintListResponse(BaseModel):
    """Response listing enrolled voiceprints."""
    count: int
    voiceprints: List[VoiceprintInfo]
