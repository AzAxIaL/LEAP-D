"""
SQLAlchemy models for the EFL Speaking Analysis Platform.

Models are organized by domain:
- course: Course management
- student: Student profiles and consent
- session: Recording sessions
- audio_file: Audio file metadata and storage
- transcript: Transcripts, utterances, words
- job: Background job tracking
- voiceprint: Voice embeddings (Phase 2)
- consent: Consent records
- assessment: CEFR/ACTFL evidence and ratings
- report: Generated reports
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, Text,
    Enum, UniqueConstraint, Index, JSON, Numeric
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base


# ============== ENUMS ==============

class ConsentStatus(str, PyEnum):
    """Consent status enumeration."""
    PENDING = "pending"
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class Role(str, PyEnum):
    """Participant role in a session."""
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    UNKNOWN = "unknown"
    MIXED = "mixed"


class AudioSourceType(str, PyEnum):
    """Type of audio source."""
    MULTI_TRACK = "multi_track"
    MIXED_FILE = "mixed_file"


class JobStatus(str, PyEnum):
    """Background job status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStage(str, PyEnum):
    """Processing pipeline stages."""
    INGEST = "ingest"
    PREPROCESS = "preprocess"
    ASR = "asr"
    ALIGNMENT = "alignment"
    DIARIZATION = "diarization"
    IDENTITY = "identity"
    TRANSCRIPT = "transcript"
    DISFLUENCY = "disfluency"
    FLUENCY_METRICS = "fluency_metrics"
    PRONUNCIATION = "pronunciation"
    INTERACTION = "interaction"
    ASSESSMENT = "assessment"
    REPORTS = "reports"


class DisfluencyType(str, PyEnum):
    """Disfluency candidate types (non-diagnostic)."""
    FILLED_PAUSE = "filled_pause"
    SILENT_PAUSE = "silent_pause"
    REPETITION_WORD = "repetition_word"
    REPETITION_PHRASE = "repetition_phrase"
    FALSE_START = "false_start"
    SELF_REPAIR = "self_repair"
    REFORMULATION = "reformulation"
    ABANDONED_UTTERANCE = "abandoned_utterance"
    LEXICAL_SEARCH = "lexical_search"
    POSSIBLE_SOUND_REPETITION = "possible_sound_repetition"
    POSSIBLE_PROLONGATION = "possible_prolongation"


class ReviewStatus(str, PyEnum):
    """Review status for candidates and assessments."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_CONTEXT = "needs_context"


class IdentitySource(str, PyEnum):
    """Source of speaker identity assignment."""
    MANUAL = "manual"
    TRACK = "track"
    VOICEPRINT = "voiceprint"
    DIARIZATION = "diarization"
    IMPORT = "import"


class CEFRLevel(str, PyEnum):
    """CEFR proficiency levels."""
    PRE_A1 = "pre_a1"
    A1 = "a1"
    A2 = "a2"
    B1 = "b1"
    B2 = "b2"
    C1 = "c1"
    C2 = "c2"


class ACTFLLevel(str, PyEnum):
    """ACTFL proficiency levels."""
    NOVICE_LOW = "novice_low"
    NOVICE_MID = "novice_mid"
    NOVICE_HIGH = "novice_high"
    INTERMEDIATE_LOW = "intermediate_low"
    INTERMEDIATE_MID = "intermediate_mid"
    INTERMEDIATE_HIGH = "intermediate_high"
    ADVANCED_LOW = "advanced_low"
    ADVANCED_MID = "advanced_mid"
    ADVANCED_HIGH = "advanced_high"
    SUPERIOR = "superior"
    DISTINGUISHED = "distinguished"


class ConstructType(str, PyEnum):
    """Assessment construct types."""
    SPOKEN_PRODUCTION = "spoken_production"
    SPOKEN_INTERACTION = "spoken_interaction"
    PHONOLOGICAL_CONTROL = "phonological_control"
    RANGE = "range"
    ACCURACY = "accuracy"
    FLUENCY = "fluency"
    COHERENCE = "coherence"
    ONLINE_CONVERSATION = "online_conversation"
    MEDIATION_TEXT = "mediation_text"
    MEDIATION_CONCEPTS = "mediation_concepts"
    MEDIATION_COMMUNICATION = "mediation_communication"
    PLURILINGUAL_BEHAVIOUR = "plurilingual_behaviour"
    INTERACTIONAL_COMPREHENSION = "interactional_comprehension"


# ============== COURSE ==============

class Course(Base):
    """Course model for organizing sessions and students."""
    __tablename__ = "courses"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    retention_days: Mapped[int] = mapped_column(Integer, default=365)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    students: Mapped[List["Student"]] = relationship(
        "Student", back_populates="course", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship(
        "Session", back_populates="course", cascade="all, delete-orphan"
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report", back_populates="course", cascade="all, delete-orphan"
    )


# ============== STUDENT ==============

class Student(Base):
    """Student profile with stable ID and first name only."""
    __tablename__ = "students"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stable_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="students")
    consents: Mapped[List["Consent"]] = relationship(
        "Consent", back_populates="student", cascade="all, delete-orphan"
    )
    voiceprints: Mapped[List["Voiceprint"]] = relationship(
        "Voiceprint", back_populates="student", cascade="all, delete-orphan"
    )
    session_participants: Mapped[List["SessionParticipant"]] = relationship(
        "SessionParticipant", back_populates="student"
    )
    assessments: Mapped[List["Assessment"]] = relationship(
        "Assessment", back_populates="student", cascade="all, delete-orphan"
    )


# ============== CONSENT ==============

class Consent(Base):
    """Consent records for privacy compliance."""
    __tablename__ = "consents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    consent_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "voiceprint", "analysis"
    status: Mapped[ConsentStatus] = mapped_column(Enum(ConsentStatus), default=ConsentStatus.PENDING)
    granted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="consents")
    
    __table_args__ = (
        Index("idx_consents_student_type", "student_id", "consent_type"),
    )


# ============== SESSION ==============

class Session(Base):
    """Recording session within a course."""
    __tablename__ = "sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    task_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    task_context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    audio_source_type: Mapped[AudioSourceType] = mapped_column(
        Enum(AudioSourceType), default=AudioSourceType.MULTI_TRACK
    )
    
    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="sessions")
    audio_files: Mapped[List["AudioFile"]] = relationship(
        "AudioFile", back_populates="session", cascade="all, delete-orphan"
    )
    participants: Mapped[List["SessionParticipant"]] = relationship(
        "SessionParticipant", back_populates="session", cascade="all, delete-orphan"
    )
    jobs: Mapped[List["Job"]] = relationship(
        "Job", back_populates="session", cascade="all, delete-orphan"
    )
    assessments: Mapped[List["Assessment"]] = relationship(
        "Assessment", back_populates="session", cascade="all, delete-orphan"
    )


class SessionParticipant(Base):
    """Participant assignment in a session."""
    __tablename__ = "session_participants"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    student_id: Mapped[Optional[int]] = mapped_column(ForeignKey("students.id"), nullable=True)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.STUDENT)
    track_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="participants")
    student: Mapped[Optional["Student"]] = relationship("Student", back_populates="session_participants")
    
    __table_args__ = (
        UniqueConstraint("session_id", "track_number", name="uq_session_track"),
    )


# ============== AUDIO FILE ==============

class AudioFile(Base):
    """Audio file metadata and storage information."""
    __tablename__ = "audio_files"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    sample_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    channels: Mapped[int] = mapped_column(Integer, default=1)
    codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    import_source: Mapped[str] = mapped_column(String(100), default="upload")
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    processing_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="audio_files")
    transcripts: Mapped[List["Transcript"]] = relationship(
        "Transcript", back_populates="audio_file", cascade="all, delete-orphan"
    )


# ============== TRANSCRIPT ==============

class Transcript(Base):
    """ASR transcript for an audio file."""
    __tablename__ = "transcripts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    audio_file_id: Mapped[int] = mapped_column(ForeignKey("audio_files.id"), nullable=False)
    asr_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    asr_model: Mapped[str] = mapped_column(String(100), nullable=False)
    asr_language: Mapped[str] = mapped_column(String(10), nullable=False)
    overall_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    word_level_confidence: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)
    raw_segments: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    audio_file: Mapped["AudioFile"] = relationship("AudioFile", back_populates="transcripts")
    utterances: Mapped[List["Utterance"]] = relationship(
        "Utterance", back_populates="transcript", cascade="all, delete-orphan"
    )


class Utterance(Base):
    """Speaker-attributed utterance within a transcript."""
    __tablename__ = "utterances"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transcript_id: Mapped[int] = mapped_column(ForeignKey("transcripts.id"), nullable=False)
    speaker_label: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "STUDENT_001", "DIAR_0"
    start_time: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    end_time: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revision_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    transcript: Mapped["Transcript"] = relationship("Transcript", back_populates="utterances")
    words: Mapped[List["Word"]] = relationship(
        "Word", back_populates="utterance", cascade="all, delete-orphan"
    )
    disfluencies: Mapped[List["DisfluencyCandidate"]] = relationship(
        "DisfluencyCandidate", back_populates="utterance", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_utterances_transcript_time", "transcript_id", "start_time"),
    )


class Word(Base):
    """Individual word with timestamps."""
    __tablename__ = "words"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    utterance_id: Mapped[int] = mapped_column(ForeignKey("utterances.id"), nullable=False)
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    start_time: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    end_time: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Relationships
    utterance: Mapped["Utterance"] = relationship("Utterance", back_populates="words")
    
    __table_args__ = (
        Index("idx_words_utterance_time", "utterance_id", "start_time"),
    )


# ============== DISFLUENCY ==============

class DisfluencyCandidate(Base):
    """Disfluency detection candidate requiring review."""
    __tablename__ = "disfluency_candidates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    utterance_id: Mapped[int] = mapped_column(ForeignKey("utterances.id"), nullable=False)
    disfluency_type: Mapped[DisfluencyType] = mapped_column(Enum(DisfluencyType), nullable=False)
    start_time: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    end_time: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    detector: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "rule_based", "timing", "crisperwhisper"
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDING
    )
    reviewer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    utterance: Mapped["Utterance"] = relationship("Utterance", back_populates="disfluencies")


# ============== JOB ==============

class Job(Base):
    """Background job for tracking processing pipeline."""
    __tablename__ = "jobs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.PENDING)
    current_stage: Mapped[Optional[JobStage]] = mapped_column(Enum(JobStage), nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    job_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="jobs")
    stage_results: Mapped[List["JobStageResult"]] = relationship(
        "JobStageResult", back_populates="job", cascade="all, delete-orphan"
    )


class JobStageResult(Base):
    """Result artifact for a specific job stage."""
    __tablename__ = "job_stage_results"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    stage: Mapped[JobStage] = mapped_column(Enum(JobStage), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success, failed, skipped
    artifact_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    stage_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="stage_results")
    
    __table_args__ = (
        UniqueConstraint("job_id", "stage", name="uq_job_stage"),
    )


# ============== VOICEPRINT (Phase 2) ==============

class Voiceprint(Base):
    """Voice embedding for speaker identification (Phase 2)."""
    __tablename__ = "voiceprints"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    embedding_data: Mapped[bytes] = mapped_column(nullable=False)  # Binary embedding
    embedding_version: Mapped[str] = mapped_column(String(50), nullable=False)
    source_audio_file_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("audio_files.id"), nullable=True
    )
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    enrollment_duration_seconds: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="voiceprints")


# ============== ASSESSMENT ==============

class Assessment(Base):
    """CEFR/ACTFL evidence-linked assessment."""
    __tablename__ = "assessments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    construct_type: Mapped[ConstructType] = mapped_column(Enum(ConstructType), nullable=False)
    
    # CEFR
    cefr_provisional_min: Mapped[Optional[CEFRLevel]] = mapped_column(
        Enum(CEFRLevel), nullable=True
    )
    cefr_provisional_max: Mapped[Optional[CEFRLevel]] = mapped_column(
        Enum(CEFRLevel), nullable=True
    )
    cefr_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cefr_evidence_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    # ACTFL (separate from CEFR)
    actfl_provisional: Mapped[Optional[ACTFLLevel]] = mapped_column(
        Enum(ACTFLLevel), nullable=True
    )
    actfl_crosswalk_label: Mapped[str] = mapped_column(
        String(50), default="indicative_only"
    )
    
    # Teacher confirmation
    teacher_confirmed_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    teacher_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDING
    )
    teacher_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    confirmed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Metadata
    coverage_indicator: Mapped[str] = mapped_column(String(20), default="sufficient")
    rubric_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_versions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    review_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="assessments")
    session: Mapped["Session"] = relationship("Session", back_populates="assessments")
    evidence_items: Mapped[List["AssessmentEvidence"]] = relationship(
        "AssessmentEvidence", back_populates="assessment", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_assessments_student_session", "student_id", "session_id"),
    )


class AssessmentEvidence(Base):
    """Individual evidence item linked to an assessment."""
    __tablename__ = "assessment_evidence"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    descriptor_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    descriptor_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp_start: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    timestamp_end: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    speaker_label: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    is_counter_evidence: Mapped[bool] = mapped_column(Boolean, default=False)
    detector_provenance: Mapped[str] = mapped_column(String(100), nullable=False)
    review_state: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="evidence_items")


# ============== REPORT ==============

class Report(Base):
    """Generated report (session, student, course)."""
    __tablename__ = "reports"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    student_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("students.id"), nullable=True
    )
    session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sessions.id"), nullable=True
    )
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)
    format: Mapped[str] = mapped_column(String(10), default="html")  # html, json, csv, pdf
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    report_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="reports")


# ============== PRONUNCIATION (Phase 3) ==============

class PronunciationCandidate(Base):
    """Pronunciation observation candidate (Phase 3)."""
    __tablename__ = "pronunciation_candidates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id"), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(100), nullable=False)
    phonetic_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acoustic_feature: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    asr_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDING
    )
    teacher_decision: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    recurrence_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    word: Mapped["Word"] = relationship("Word")


# ============== INTERACTION (Phase 3) ==============

class InteractionPair(Base):
    """Instructor prompt / student response pair (Phase 3)."""
    __tablename__ = "interaction_pairs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    prompt_utterance_id: Mapped[int] = mapped_column(Integer, nullable=False)
    response_utterance_id: Mapped[int] = mapped_column(Integer, nullable=False)
    response_latency_ms: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
