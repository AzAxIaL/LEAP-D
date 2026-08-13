"""Pydantic schemas for disfluency and fluency metrics."""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

from app.models import DisfluencyType, ReviewStatus


class DisfluencyCandidateBase(BaseModel):
    """Base schema for disfluency candidate."""
    utterance_id: Optional[str] = None
    start_time: float
    end_time: float
    disfluency_type: DisfluencyType
    evidence_text: str
    detector_source: str
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DisfluencyCandidateCreate(DisfluencyCandidateBase):
    """Schema for creating a disfluency candidate."""
    session_id: str


class DisfluencyCandidateResponse(DisfluencyCandidateBase):
    """Schema for disfluency candidate response."""
    id: str
    session_id: str
    review_status: ReviewStatus
    reviewer: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DisfluencyReviewRequest(BaseModel):
    """Schema for reviewing a disfluency candidate."""
    status: ReviewStatus
    reviewer: str
    notes: Optional[str] = None


class DisfluencyBulkReviewRequest(BaseModel):
    """Schema for bulk review of disfluency candidates."""
    candidate_ids: list[str]
    status: ReviewStatus
    reviewer: str


class FluencyMetricsBase(BaseModel):
    """Base schema for fluency metrics."""
    student_id: str
    session_id: str
    computed_at: datetime


class FluencyCounts(BaseModel):
    """Basic count metrics."""
    total_words: int
    total_utterances: int
    speaking_time_seconds: float
    participation_share: float


class RateMeasures(BaseModel):
    """Speech rate measures."""
    speech_rate_wpm: Optional[float] = None
    articulation_rate_wpm: Optional[float] = None
    speech_rate_eligible: bool
    articulation_rate_eligible: bool


class PauseMeasures(BaseModel):
    """Pause-related measures."""
    total_pause_duration: float
    pause_count: int
    mean_pause_duration: Optional[float] = None
    long_pauses_count: int
    long_pauses_per_minute: Optional[float] = None


class DisfluencyMeasures(BaseModel):
    """Disfluency-related measures."""
    filled_pause_count: int
    repetition_count: int
    repair_count: int
    false_start_count: int
    filled_pause_rate: Optional[float] = None
    repetition_rate: Optional[float] = None
    repair_rate: Optional[float] = None
    overall_disfluency_rate: Optional[float] = None


class UtteranceMeasures(BaseModel):
    """Utterance-related measures."""
    mean_utterance_length: Optional[float] = None
    utterance_length_std: Optional[float] = None
    min_utterance_length: int
    max_utterance_length: int


class LexicalDiversityMeasures(BaseModel):
    """Lexical diversity measures."""
    type_token_ratio: Optional[float] = None
    mtld_score: Optional[float] = None
    lexical_diversity_eligible: bool


class QualityFlags(BaseModel):
    """Quality and eligibility flags."""
    timing_quality: str
    sample_size_warning: bool
    missingness_notes: list[str]


class DisfluencyMetricsResponse(BaseModel):
    """Complete fluency metrics response."""
    student_id: str
    session_id: str
    computed_at: datetime
    basic_counts: FluencyCounts
    rate_measures: RateMeasures
    pause_measures: PauseMeasures
    disfluency_measures: DisfluencyMeasures
    utterance_measures: UtteranceMeasures
    lexical_diversity: LexicalDiversityMeasures
    quality_flags: QualityFlags
    
    class Config:
        from_attributes = True
