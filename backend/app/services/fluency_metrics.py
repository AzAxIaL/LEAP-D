"""Fluency metrics computation service.

Computes per-student/session metrics with eligibility flags and denominator definitions.
All metrics include uncertainty indicators and sample size warnings.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session, joinedload

from app.models import (
    DisfluencyCandidate, DisfluencyType, ReviewStatus,
    Utterance, AudioFile, Student
)


@dataclass
class FluencyMetrics:
    """Computed fluency metrics for a student session."""
    
    # Identity
    student_id: str
    session_id: str
    computed_at: datetime = field(default_factory=datetime.utcnow)
    
    # Basic counts
    total_words: int = 0
    total_utterances: int = 0
    speaking_time_seconds: float = 0.0
    participation_share: float = 0.0  # 0.0-1.0
    
    # Rate measures
    speech_rate_wpm: Optional[float] = None  # Words per minute (total time)
    articulation_rate_wpm: Optional[float] = None  # Words per minute (speaking time only)
    speech_rate_eligible: bool = False
    articulation_rate_eligible: bool = False
    
    # Pause measures
    total_pause_duration: float = 0.0
    pause_count: int = 0
    mean_pause_duration: Optional[float] = None
    long_pauses_count: int = 0  # Pauses > 1 second
    long_pauses_per_minute: Optional[float] = None
    
    # Disfluency measures (only from ACCEPTED candidates)
    filled_pause_count: int = 0
    repetition_count: int = 0
    repair_count: int = 0
    false_start_count: int = 0
    
    filled_pause_rate: Optional[float] = None  # Per 100 words
    repetition_rate: Optional[float] = None  # Per 100 words
    repair_rate: Optional[float] = None  # Per 100 words
    overall_disfluency_rate: Optional[float] = None  # Per 100 words
    
    # Utterance measures
    mean_utterance_length: Optional[float] = None
    utterance_length_std: Optional[float] = None
    min_utterance_length: int = 0
    max_utterance_length: int = 0
    
    # Lexical diversity (with minimum sample warnings)
    type_token_ratio: Optional[float] = None
    mtld_score: Optional[float] = None  # Moving Average Type-Token Ratio
    lexical_diversity_eligible: bool = False
    
    # Quality flags
    timing_quality: str = "good"  # "good", "poor", "unknown"
    sample_size_warning: bool = False
    missingness_notes: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "student_id": self.student_id,
            "session_id": self.session_id,
            "computed_at": self.computed_at.isoformat(),
            "basic_counts": {
                "total_words": self.total_words,
                "total_utterances": self.total_utterances,
                "speaking_time_seconds": self.speaking_time_seconds,
                "participation_share": self.participation_share
            },
            "rate_measures": {
                "speech_rate_wpm": self.speech_rate_wpm,
                "articulation_rate_wpm": self.articulation_rate_wpm,
                "speech_rate_eligible": self.speech_rate_eligible,
                "articulation_rate_eligible": self.articulation_rate_eligible
            },
            "pause_measures": {
                "total_pause_duration": self.total_pause_duration,
                "pause_count": self.pause_count,
                "mean_pause_duration": self.mean_pause_duration,
                "long_pauses_count": self.long_pauses_count,
                "long_pauses_per_minute": self.long_pauses_per_minute
            },
            "disfluency_measures": {
                "filled_pause_count": self.filled_pause_count,
                "repetition_count": self.repetition_count,
                "repair_count": self.repair_count,
                "false_start_count": self.false_start_count,
                "filled_pause_rate": self.filled_pause_rate,
                "repetition_rate": self.repetition_rate,
                "repair_rate": self.repair_rate,
                "overall_disfluency_rate": self.overall_disfluency_rate
            },
            "utterance_measures": {
                "mean_utterance_length": self.mean_utterance_length,
                "utterance_length_std": self.utterance_length_std,
                "min_utterance_length": self.min_utterance_length,
                "max_utterance_length": self.max_utterance_length
            },
            "lexical_diversity": {
                "type_token_ratio": self.type_token_ratio,
                "mtld_score": self.mtld_score,
                "lexical_diversity_eligible": self.lexical_diversity_eligible
            },
            "quality_flags": {
                "timing_quality": self.timing_quality,
                "sample_size_warning": self.sample_size_warning,
                "missingness_notes": self.missingness_notes
            }
        }


class FluencyMetricsService:
    """Service for computing fluency metrics from reviewed disfluency data."""
    
    # Minimum samples for reliable metrics
    MIN_WORDS_FOR_RATE = 50
    MIN_UTTERANCES_FOR_MEAN = 5
    MIN_WORDS_FOR_LEXICAL = 100
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def compute_metrics(
        self,
        student_id: str,
        session_id: str
    ) -> FluencyMetrics:
        """Compute all fluency metrics for a student session."""
        metrics = FluencyMetrics(student_id=student_id, session_id=session_id)
        
        # Get all utterances for this student in this session
        utterances = self.db.query(Utterance).join(AudioFile).filter(
            AudioFile.session_id == session_id,
            Utterance.speaker_id == student_id
        ).all()
        
        if not utterances:
            metrics.missingness_notes.append("No utterances found for student")
            return metrics
        
        # Get accepted disfluency candidates
        accepted_candidates = self.db.query(DisfluencyCandidate).filter(
            DisfluencyCandidate.session_id == session_id,
            DisfluencyCandidate.review_status == ReviewStatus.ACCEPTED
        ).all()
        
        # Filter to this student's utterances
        utterance_ids = {u.id for u in utterances}
        student_candidates = [
            c for c in accepted_candidates 
            if c.utterance_id in utterance_ids
        ]
        
        # Compute basic counts
        metrics.total_utterances = len(utterances)
        metrics.total_words = sum(u.word_count or 0 for u in utterances)
        metrics.speaking_time_seconds = sum(
            (u.end_time - u.start_time) for u in utterances if u.start_time and u.end_time
        )
        
        # Compute participation share
        total_session_time = self._get_total_session_speaking_time(session_id)
        if total_session_time > 0:
            metrics.participation_share = metrics.speaking_time_seconds / total_session_time
        
        # Compute rate measures
        if metrics.speaking_time_seconds > 0 and metrics.total_words >= self.MIN_WORDS_FOR_RATE:
            metrics.speech_rate_wpm = (metrics.total_words / metrics.speaking_time_seconds) * 60
            metrics.speech_rate_eligible = True
        else:
            metrics.missingness_notes.append(
                f"Insufficient words ({metrics.total_words}) for speech rate calculation"
            )
            metrics.sample_size_warning = True
        
        # Articulation rate (excluding pauses) - simplified estimate
        total_pause_time = sum(
            c.end_time - c.start_time 
            for c in student_candidates 
            if c.disfluency_type == DisfluencyType.SILENT_PAUSE
        )
        speaking_time_excl_pauses = metrics.speaking_time_seconds - total_pause_time
        
        if speaking_time_excl_pauses > 0 and metrics.total_words >= self.MIN_WORDS_FOR_RATE:
            metrics.articulation_rate_wpm = (metrics.total_words / speaking_time_excl_pauses) * 60
            metrics.articulation_rate_eligible = True
        
        # Compute pause measures
        silent_pauses = [
            c for c in student_candidates 
            if c.disfluency_type == DisfluencyType.SILENT_PAUSE
        ]
        metrics.pause_count = len(silent_pauses)
        metrics.total_pause_duration = sum(c.end_time - c.start_time for c in silent_pauses)
        
        if metrics.pause_count > 0:
            metrics.mean_pause_duration = metrics.total_pause_duration / metrics.pause_count
        
        metrics.long_pauses_count = len([
            c for c in silent_pauses 
            if (c.end_time - c.start_time) > 1.0
        ])
        
        if metrics.speaking_time_seconds > 0:
            metrics.long_pauses_per_minute = (
                metrics.long_pauses_count / metrics.speaking_time_seconds
            ) * 60
        
        # Compute disfluency counts by type
        type_counts = {}
        for candidate in student_candidates:
            dtype = candidate.disfluency_type
            type_counts[dtype] = type_counts.get(dtype, 0) + 1
        
        metrics.filled_pause_count = type_counts.get(DisfluencyType.FILLED_PAUSE, 0)
        metrics.repetition_count = type_counts.get(DisfluencyType.REPETITION, 0)
        metrics.repair_count = (
            type_counts.get(DisfluencyType.SELF_REPAIR, 0) +
            type_counts.get(DisfluencyType.REPAIR_SUCCESS, 0)
        )
        metrics.false_start_count = type_counts.get(DisfluencyType.FALSE_START, 0)
        
        # Compute rates per 100 words
        if metrics.total_words >= self.MIN_WORDS_FOR_RATE:
            divisor = metrics.total_words / 100
            metrics.filled_pause_rate = metrics.filled_pause_count / divisor
            metrics.repetition_rate = metrics.repetition_count / divisor
            metrics.repair_rate = metrics.repair_count / divisor
            metrics.overall_disfluency_rate = (
                metrics.filled_pause_count + 
                metrics.repetition_count + 
                metrics.repair_count + 
                metrics.false_start_count
            ) / divisor
        
        # Compute utterance measures
        utterance_lengths = [u.word_count or 0 for u in utterances]
        if len(utterance_lengths) >= self.MIN_UTTERANCES_FOR_MEAN:
            metrics.mean_utterance_length = sum(utterance_lengths) / len(utterance_lengths)
            metrics.min_utterance_length = min(utterance_lengths)
            metrics.max_utterance_length = max(utterance_lengths)
            
            # Standard deviation
            if len(utterance_lengths) > 1:
                mean = metrics.mean_utterance_length
                variance = sum((x - mean) ** 2 for x in utterance_lengths) / len(utterance_lengths)
                metrics.utterance_length_std = variance ** 0.5
        else:
            metrics.sample_size_warning = True
            metrics.missingness_notes.append(
                f"Insufficient utterances ({len(utterance_lengths)}) for mean length"
            )
        
        # Compute lexical diversity
        all_words = []
        for u in utterances:
            if u.transcript_text:
                words = u.transcript_text.lower().split()
                # Remove punctuation
                import re
                words = [re.sub(r'[^\w]', '', w) for w in words if w]
                all_words.extend(words)
        
        if len(all_words) >= self.MIN_WORDS_FOR_LEXICAL:
            unique_words = set(all_words)
            metrics.type_token_ratio = len(unique_words) / len(all_words)
            metrics.mtld_score = self._compute_mtld(all_words)
            metrics.lexical_diversity_eligible = True
        else:
            metrics.missingness_notes.append(
                f"Insufficient words ({len(all_words)}) for lexical diversity"
            )
            metrics.sample_size_warning = True
        
        # Timing quality assessment
        utterances_with_timing = [
            u for u in utterances 
            if u.start_time is not None and u.end_time is not None
        ]
        if len(utterances_with_timing) < len(utterances) * 0.8:
            metrics.timing_quality = "poor"
            metrics.missingness_notes.append("Many utterances lack reliable timestamps")
        elif len(utterances_with_timing) == 0:
            metrics.timing_quality = "unknown"
        
        return metrics
    
    def _get_total_session_speaking_time(self, session_id: str) -> float:
        """Get total speaking time across all students in session."""
        utterances = self.db.query(Utterance).join(AudioFile).filter(
            AudioFile.session_id == session_id
        ).all()
        
        return sum(
            (u.end_time - u.start_time) 
            for u in utterances 
            if u.start_time and u.end_time
        )
    
    def _compute_mtld(self, words: list[str], threshold: float = 0.72) -> float:
        """
        Compute Moving Average Type-Token Ratio (MTLD).
        
        More robust than simple TTR for varying text lengths.
        """
        if len(words) < 10:
            return 0.0
        
        # Forward pass
        factors_forward = 0
        current_words = []
        current_ttr = 1.0
        
        for word in words:
            current_words.append(word)
            unique = len(set(current_words))
            total = len(current_words)
            current_ttr = unique / total
            
            if current_ttr <= threshold:
                factors_forward += 1
                current_words = []
        
        # Handle final segment
        if current_words:
            unique = len(set(current_words))
            total = len(current_words)
            current_ttr = unique / total
            factors_forward += (1.0 - current_ttr) / (1.0 - threshold)
        
        # Backward pass
        factors_backward = 0
        current_words = []
        
        for word in reversed(words):
            current_words.insert(0, word)
            unique = len(set(current_words))
            total = len(current_words)
            current_ttr = unique / total
            
            if current_ttr <= threshold:
                factors_backward += 1
                current_words = []
        
        # Handle final segment
        if current_words:
            unique = len(set(current_words))
            total = len(current_words)
            current_ttr = unique / total
            factors_backward += (1.0 - current_ttr) / (1.0 - threshold)
        
        # Average of forward and backward
        total_factors = factors_forward + factors_backward
        if total_factors == 0:
            return 0.0
        
        mtld = len(words) / (total_factors / 2)
        return min(100.0, mtld)  # Cap at 100
    
    def get_longitudinal_metrics(
        self,
        student_id: str,
        course_id: str,
        limit: int = 20
    ) -> list[FluencyMetrics]:
        """Get fluency metrics across multiple sessions for trend analysis."""
        # Get all sessions for this student in the course
        from app.models import Session, AudioFile
        
        sessions = self.db.query(Session).join(AudioFile).filter(
            Session.course_id == course_id,
            AudioFile.student_id == student_id
        ).order_by(Session.session_date.desc()).limit(limit).all()
        
        metrics_list = []
        for session in sessions:
            metrics = self.compute_metrics(student_id, session.id)
            metrics_list.append(metrics)
        
        return metrics_list
    
    def compute_session_aggregate(self, session_id: str) -> dict:
        """Compute aggregate metrics for entire session (all students)."""
        from app.models import AudioFile
        
        audio_files = self.db.query(AudioFile).filter(
            AudioFile.session_id == session_id
        ).all()
        
        student_metrics = {}
        for audio_file in audio_files:
            if audio_file.student_id:
                metrics = self.compute_metrics(audio_file.student_id, session_id)
                student_metrics[audio_file.student_id] = metrics.to_dict()
        
        return {
            "session_id": session_id,
            "student_count": len(student_metrics),
            "students": student_metrics
        }
