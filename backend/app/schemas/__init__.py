"""
Pydantic schemas for API request/response validation.
Organized by domain to match models.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models import (
    ConsentStatus, Role, AudioSourceType, JobStatus, JobStage,
    DisfluencyType, ReviewStatus, CEFRLevel, ACTFLLevel, ConstructType
)


# ============== SHARED ==============

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    """Mixin for created/updated timestamps."""
    created_at: datetime
    updated_at: Optional[datetime] = None


# ============== COURSE ==============

class CourseBase(BaseModel):
    """Base course schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    retention_days: int = Field(default=365, ge=1)


class CourseCreate(CourseBase):
    """Schema for creating a course."""
    pass


class CourseUpdate(BaseModel):
    """Schema for updating a course."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    retention_days: Optional[int] = Field(None, ge=1)
    is_archived: Optional[bool] = None


class CourseResponse(CourseBase, TimestampMixin):
    """Course response schema."""
    id: int
    is_archived: bool = False
    
    class Config:
        from_attributes = True


# ============== STUDENT ==============

class StudentBase(BaseModel):
    """Base student schema."""
    stable_id: str = Field(..., min_length=1, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)


class StudentCreate(StudentBase):
    """Schema for creating a student."""
    course_id: int


class StudentImportItem(BaseModel):
    """Schema for importing a student from CSV."""
    stable_id: str
    first_name: str


class StudentImportRequest(BaseModel):
    """Schema for bulk student import."""
    students: List[StudentImportItem]


class StudentResponse(StudentBase, TimestampMixin):
    """Student response schema."""
    id: int
    course_id: int
    is_active: bool = True
    
    class Config:
        from_attributes = True


# ============== CONSENT ==============

class ConsentBase(BaseModel):
    """Base consent schema."""
    consent_type: str
    status: ConsentStatus = ConsentStatus.PENDING


class ConsentCreate(ConsentBase):
    """Schema for creating consent."""
    student_id: int


class ConsentResponse(BaseModel):
    """Consent response schema."""
    id: int
    student_id: int
    consent_type: str
    status: ConsentStatus
    granted_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============== SESSION ==============

class SessionBase(BaseModel):
    """Base session schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    recorded_at: Optional[datetime] = None
    task_type: Optional[str] = None
    task_context: Optional[Dict[str, Any]] = None
    audio_source_type: AudioSourceType = AudioSourceType.MULTI_TRACK


class SessionCreate(SessionBase):
    """Schema for creating a session."""
    course_id: int


class SessionResponse(SessionBase, TimestampMixin):
    """Session response schema."""
    id: int
    course_id: int
    
    class Config:
        from_attributes = True


class SessionParticipantBase(BaseModel):
    """Base session participant schema."""
    role: Role = Role.STUDENT
    track_number: Optional[int] = None
    display_name: Optional[str] = None


class SessionParticipantCreate(SessionParticipantBase):
    """Schema for creating a participant."""
    session_id: int
    student_id: Optional[int] = None


class SessionParticipantResponse(BaseModel):
    """Session participant response schema."""
    id: int
    session_id: int
    student_id: Optional[int] = None
    role: Role
    track_number: Optional[int] = None
    display_name: Optional[str] = None
    
    class Config:
        from_attributes = True


# ============== AUDIO FILE ==============

class AudioFileResponse(BaseModel):
    """Audio file response schema."""
    id: int
    session_id: int
    original_filename: str
    stored_path: str
    content_hash: str
    file_size_bytes: int
    duration_seconds: float
    sample_rate: int
    channels: int
    codec: Optional[str] = None
    import_source: str
    imported_at: datetime
    is_processed: bool = False
    processed_path: Optional[str] = None
    processing_metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


# ============== TRANSCRIPT ==============

class WordBase(BaseModel):
    """Base word schema."""
    text: str
    start_time: float
    end_time: float
    confidence: Optional[float] = None


class WordResponse(WordBase):
    """Word response schema."""
    id: int
    utterance_id: int
    
    class Config:
        from_attributes = True


class UtteranceBase(BaseModel):
    """Base utterance schema."""
    speaker_label: str
    start_time: float
    end_time: float
    text: str
    confidence: Optional[float] = None


class UtteranceCreate(UtteranceBase):
    """Schema for creating an utterance."""
    transcript_id: int


class UtteranceResponse(UtteranceBase):
    """Utterance response schema."""
    id: int
    transcript_id: int
    is_reviewed: bool = False
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    revision_notes: Optional[str] = None
    words: List[WordResponse] = []
    
    class Config:
        from_attributes = True


class TranscriptResponse(BaseModel):
    """Transcript response schema."""
    id: int
    audio_file_id: int
    asr_provider: str
    asr_model: str
    asr_language: str
    overall_confidence: Optional[float] = None
    word_level_confidence: bool = False
    created_at: datetime
    version: int = 1
    utterances: List[UtteranceResponse] = []
    
    class Config:
        from_attributes = True


# ============== DISFLUENCY ==============

class DisfluencyCandidateBase(BaseModel):
    """Base disfluency candidate schema."""
    disfluency_type: DisfluencyType
    start_time: float
    end_time: float
    evidence_text: str
    detector: str
    confidence: float


class DisfluencyCandidateCreate(DisfluencyCandidateBase):
    """Schema for creating a disfluency candidate."""
    utterance_id: int


class DisfluencyCandidateResponse(DisfluencyCandidateBase):
    """Disfluency candidate response schema."""
    id: int
    utterance_id: int
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DisfluencyReviewRequest(BaseModel):
    """Schema for reviewing a disfluency candidate."""
    review_status: ReviewStatus
    review_notes: Optional[str] = None


# ============== JOB ==============

class JobStageResultResponse(BaseModel):
    """Job stage result response schema."""
    id: int
    job_id: int
    stage: JobStage
    status: str
    artifact_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    logs: Optional[str] = None
    duration_seconds: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    """Job response schema."""
    id: int
    session_id: int
    job_type: str
    status: JobStatus
    current_stage: Optional[JobStage] = None
    progress_percent: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    metadata: Optional[Dict[str, Any]] = None
    stage_results: List[JobStageResultResponse] = []
    
    class Config:
        from_attributes = True


# ============== ASSESSMENT ==============

class AssessmentEvidenceBase(BaseModel):
    """Base assessment evidence schema."""
    evidence_type: str
    descriptor_id: Optional[str] = None
    descriptor_text: Optional[str] = None
    timestamp_start: float
    timestamp_end: float
    transcript_text: str
    speaker_label: str
    confidence: float
    is_counter_evidence: bool = False
    detector_provenance: str


class AssessmentEvidenceResponse(AssessmentEvidenceBase):
    """Assessment evidence response schema."""
    id: int
    assessment_id: int
    review_state: ReviewStatus = ReviewStatus.PENDING
    created_at: datetime
    
    class Config:
        from_attributes = True


class AssessmentBase(BaseModel):
    """Base assessment schema."""
    construct_type: ConstructType
    cefr_provisional_min: Optional[CEFRLevel] = None
    cefr_provisional_max: Optional[CEFRLevel] = None
    cefr_confidence: Optional[float] = None
    actfl_provisional: Optional[ACTFLLevel] = None
    coverage_indicator: str = "sufficient"
    rubric_version: str


class AssessmentCreate(AssessmentBase):
    """Schema for creating an assessment."""
    student_id: int
    session_id: int


class AssessmentTeacherUpdate(BaseModel):
    """Schema for teacher confirmation of assessment."""
    teacher_confirmed_level: Optional[str] = None
    teacher_status: ReviewStatus
    teacher_notes: Optional[str] = None


class AssessmentResponse(AssessmentBase):
    """Assessment response schema."""
    id: int
    student_id: int
    session_id: int
    actfl_crosswalk_label: str = "indicative_only"
    teacher_confirmed_level: Optional[str] = None
    teacher_status: ReviewStatus = ReviewStatus.PENDING
    teacher_notes: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None
    model_versions: Optional[Dict[str, Any]] = None
    review_timestamp: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    evidence_items: List[AssessmentEvidenceResponse] = []
    
    class Config:
        from_attributes = True


# ============== REPORT ==============

class ReportResponse(BaseModel):
    """Report response schema."""
    id: int
    course_id: int
    student_id: Optional[int] = None
    session_id: Optional[int] = None
    report_type: str
    title: str
    generated_at: datetime
    version: int = 1
    format: str = "html"
    file_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


# ============== VOICEPRINT (Phase 2) ==============

class VoiceprintResponse(BaseModel):
    """Voiceprint response schema (excludes embedding data)."""
    id: int
    student_id: int
    embedding_version: str
    quality_score: Optional[float] = None
    enrollment_duration_seconds: Optional[float] = None
    is_active: bool = True
    enrolled_at: datetime
    deleted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============== COMPOSITE RESPONSES ==============

class SessionDetailResponse(SessionResponse):
    """Session with related data."""
    audio_files: List[AudioFileResponse] = []
    participants: List[SessionParticipantResponse] = []
    jobs: List[JobResponse] = []


class StudentDetailResponse(StudentResponse):
    """Student with related data."""
    consents: List[ConsentResponse] = []
    voiceprints: List[VoiceprintResponse] = []


class CourseDetailResponse(CourseResponse):
    """Course with related data."""
    students: List[StudentResponse] = []
    sessions: List[SessionResponse] = []
