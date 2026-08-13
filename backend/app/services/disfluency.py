"""Disfluency detection service with review-first workflow.

Implements hybrid detection pipeline:
- Transcript rules and timing/VAD signals
- Acoustic features where validated
- Optional crisperwhisper provider output
- Local LLM candidate classification (optional)

Taxonomy separates learner-language phenomena from clinical interpretation.
All candidates require human review before inclusion in metrics.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import DisfluencyCandidate, DisfluencyType, ReviewStatus


class DisfluencyCategory(str, Enum):
    """Categories for disfluency phenomena."""
    FILLED_PAUSE = "filled_pause"
    SILENT_PAUSE = "silent_pause"
    REPETITION_WORD = "repetition_word"
    REPETITION_PHRASE = "repetition_phrase"
    FALSE_START = "false_start"
    SELF_REPAIR = "self_repair"
    REFORMULATION = "reformulation"
    ABANDONED_UTTERANCE = "abandoned_utterance"
    LEXICAL_SEARCH = "lexical_search"
    REPAIR_SUCCESS = "repair_success"
    POSSIBLE_SOUND_REPETITION = "possible_sound_repetition"  # Non-diagnostic, review-required
    POSSIBLE_PROLONGATION = "possible_prolongation"  # Non-diagnostic, review-required


@dataclass
class DisfluencyEvidence:
    """Detected disfluency candidate with evidence."""
    id: str
    session_id: str
    utterance_id: Optional[str]
    start_time: float
    end_time: float
    category: DisfluencyCategory
    evidence_text: str
    detector: str  # e.g., "rule_based", "timing", "acoustic", "crisperwhisper", "llm"
    confidence: float  # 0.0-1.0
    severity: Optional[str] = None  # "low", "medium", "high" or None
    impact_note: Optional[str] = None  # Communicative impact note
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "utterance_id": self.utterance_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "category": self.category.value,
            "evidence_text": self.evidence_text,
            "detector": self.detector,
            "confidence": self.confidence,
            "severity": self.severity,
            "impact_note": self.impact_note,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class DisfluencyDetector:
    """Hybrid disfluency detection pipeline."""
    
    # Filled pause patterns (English)
    FILLED_PAUSE_PATTERNS = [
        r"\b(um|uh|er|erm|ah|eh)\b",
        r"\b(you know|like|I mean|sort of|kind of)\b",
    ]
    
    # Japanese filler words (preserve verbatim, not errors)
    JAPANESE_FILLERS = [
        r"\b(えーと|あのー|まあ|なんか|そのー)\b",
    ]
    
    # Repetition pattern: word repeated immediately
    REPETITION_PATTERN = r'\b(\w+)\s+\1\b'
    
    # False start pattern: incomplete phrase followed by restart
    FALSE_START_INDICATORS = [
        r"\b(I was|I am|He was|She was|They were)\s+\w+\s+but\s+",
        r"\b(The|A|An)\s+\w+\s+uh\s+\w+",
    ]
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def detect_from_transcript(
        self,
        utterance_id: str,
        transcript_text: str,
        start_time: float,
        word_timestamps: list[dict]
    ) -> list[DisfluencyEvidence]:
        """Detect disfluency candidates from transcript and timing data."""
        candidates = []
        
        # Detect filled pauses
        candidates.extend(
            self._detect_filled_pauses(
                utterance_id, transcript_text, start_time, word_timestamps
            )
        )
        
        # Detect repetitions
        candidates.extend(
            self._detect_repetitions(
                utterance_id, transcript_text, start_time, word_timestamps
            )
        )
        
        # Detect false starts
        candidates.extend(
            self._detect_false_starts(
                utterance_id, transcript_text, start_time, word_timestamps
            )
        )
        
        return candidates
    
    def _detect_filled_pauses(
        self,
        utterance_id: str,
        text: str,
        start_time: float,
        word_timestamps: list[dict]
    ) -> list[DisfluencyEvidence]:
        """Detect filled pauses including Japanese fillers."""
        candidates = []
        text_lower = text.lower()
        
        # English filled pauses
        for pattern in self.FILLED_PAUSE_PATTERNS:
            for match in re.finditer(pattern, text_lower, re.IGNORECASE):
                # Find corresponding timestamp
                matched_word = match.group(0)
                ts_data = self._find_word_timestamp(matched_word, word_timestamps)
                
                if ts_data:
                    candidate = DisfluencyEvidence(
                        id=str(uuid4()),
                        session_id="",  # Will be set by service
                        utterance_id=utterance_id,
                        start_time=start_time + ts_data["start"],
                        end_time=start_time + ts_data["end"],
                        category=DisfluencyCategory.FILLED_PAUSE,
                        evidence_text=matched_word,
                        detector="rule_based",
                        confidence=0.85,
                        metadata={
                            "pattern": pattern,
                            "language": "en"
                        }
                    )
                    candidates.append(candidate)
        
        # Japanese filled pauses - treat as normal planning phenomena
        for pattern in self.JAPANESE_FILLERS:
            for match in re.finditer(pattern, text):
                matched_word = match.group(0)
                ts_data = self._find_word_timestamp(matched_word, word_timestamps)
                
                if ts_data:
                    candidate = DisfluencyEvidence(
                        id=str(uuid4()),
                        session_id="",
                        utterance_id=utterance_id,
                        start_time=start_time + ts_data["start"],
                        end_time=start_time + ts_data["end"],
                        category=DisfluencyCategory.FILLED_PAUSE,
                        evidence_text=matched_word,
                        detector="rule_based",
                        confidence=0.90,
                        metadata={
                            "pattern": pattern,
                            "language": "ja",
                            "note": "Japanese filler - normal L2 planning phenomenon"
                        }
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _detect_repetitions(
        self,
        utterance_id: str,
        text: str,
        start_time: float,
        word_timestamps: list[dict]
    ) -> list[DisfluencyEvidence]:
        """Detect word/phrase repetitions."""
        candidates = []
        
        for match in re.finditer(self.REPETITION_PATTERN, text, re.IGNORECASE):
            repeated_word = match.group(1)
            
            # Find timestamps for both occurrences
            ts_data = self._find_word_timestamp(repeated_word, word_timestamps)
            
            if ts_data:
                # Estimate end time based on word duration
                word_duration = ts_data["end"] - ts_data["start"]
                candidate = DisfluencyEvidence(
                    id=str(uuid4()),
                    session_id="",
                    utterance_id=utterance_id,
                    start_time=start_time + ts_data["start"],
                    end_time=start_time + ts_data["end"] + word_duration,
                    category=DisfluencyCategory.REPETITION_WORD,
                    evidence_text=f"{repeated_word} {repeated_word}",
                    detector="rule_based",
                    confidence=0.80,
                    metadata={
                        "repeated_word": repeated_word,
                        "position": match.start()
                    }
                )
                candidates.append(candidate)
        
        return candidates
    
    def _detect_false_starts(
        self,
        utterance_id: str,
        text: str,
        start_time: float,
        word_timestamps: list[dict]
    ) -> list[DisfluencyEvidence]:
        """Detect false starts and abandoned utterances."""
        candidates = []
        
        for pattern in self.FALSE_START_INDICATORS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matched_text = match.group(0)
                
                ts_data = self._find_word_timestamp(matched_text.split()[0], word_timestamps)
                
                if ts_data:
                    candidate = DisfluencyEvidence(
                        id=str(uuid4()),
                        session_id="",
                        utterance_id=utterance_id,
                        start_time=start_time + ts_data["start"],
                        end_time=start_time + ts_data["start"] + 1.0,  # Approximate
                        category=DisfluencyCategory.FALSE_START,
                        evidence_text=matched_text.strip(),
                        detector="rule_based",
                        confidence=0.70,
                        metadata={
                            "pattern": pattern,
                            "indicator_type": "restart"
                        }
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _find_word_timestamp(
        self,
        word: str,
        word_timestamps: list[dict]
    ) -> Optional[dict]:
        """Find timestamp data for a specific word."""
        word_lower = word.lower().strip()
        
        for ts in word_timestamps:
            ts_word = ts.get("word", "").lower().strip()
            # Remove punctuation for matching
            ts_word_clean = re.sub(r'[^\w]', '', ts_word)
            word_clean = re.sub(r'[^\w]', '', word_lower)
            
            if ts_word_clean == word_clean:
                return {
                    "word": ts.get("word"),
                    "start": ts.get("start", 0.0),
                    "end": ts.get("end", 0.0),
                    "confidence": ts.get("confidence", 1.0)
                }
        
        return None
    
    def detect_from_timing(
        self,
        utterance_id: str,
        word_timestamps: list[dict],
        silence_threshold: float = 0.3
    ) -> list[DisfluencyEvidence]:
        """Detect silent pauses from timing gaps."""
        candidates = []
        
        for i in range(len(word_timestamps) - 1):
            current_word = word_timestamps[i]
            next_word = word_timestamps[i + 1]
            
            gap = next_word["start"] - current_word["end"]
            
            if gap >= silence_threshold:
                candidate = DisfluencyEvidence(
                    id=str(uuid4()),
                    session_id="",
                    utterance_id=utterance_id,
                    start_time=current_word["end"],
                    end_time=next_word["start"],
                    category=DisfluencyCategory.SILENT_PAUSE,
                    evidence_text="[silent pause]",
                    detector="timing",
                    confidence=min(0.95, 0.5 + gap),
                    severity="low" if gap < 0.5 else ("medium" if gap < 1.0 else "high"),
                    metadata={
                        "gap_duration": gap,
                        "threshold": silence_threshold,
                        "preceding_word": current_word.get("word"),
                        "following_word": next_word.get("word")
                    }
                )
                candidates.append(candidate)
        
        return candidates


class DisfluencyService:
    """Service for managing disfluency detection and review workflow."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.detector = DisfluencyDetector(db_session)
    
    def create_candidates(
        self,
        session_id: str,
        utterance_id: str,
        transcript_text: str,
        start_time: float,
        word_timestamps: list[dict],
        detectors: list[str]
    ) -> list[DisfluencyCandidate]:
        """Create disfluency candidates for review."""
        candidates = []
        
        # Run transcript-based detection
        if "rule_based" in detectors or "timing" in detectors:
            transcript_candidates = self.detector.detect_from_transcript(
                utterance_id, transcript_text, start_time, word_timestamps
            )
            candidates.extend(transcript_candidates)
        
        # Run timing-based detection
        if "timing" in detectors:
            timing_candidates = self.detector.detect_from_timing(
                utterance_id, word_timestamps
            )
            candidates.extend(timing_candidates)
        
        # Store candidates in database
        db_candidates = []
        for cand in candidates:
            cand.session_id = session_id
            
            # Map category to DisfluencyType enum
            type_mapping = {
                DisfluencyCategory.FILLED_PAUSE: DisfluencyType.FILLED_PAUSE,
                DisfluencyCategory.SILENT_PAUSE: DisfluencyType.SILENT_PAUSE,
                DisfluencyCategory.REPETITION_WORD: DisfluencyType.REPETITION,
                DisfluencyCategory.REPETITION_PHRASE: DisfluencyType.REPETITION,
                DisfluencyCategory.FALSE_START: DisfluencyType.FALSE_START,
                DisfluencyCategory.SELF_REPAIR: DisfluencyType.SELF_REPAIR,
                DisfluencyCategory.REFORMULATION: DisfluencyType.REFORMULATION,
                DisfluencyCategory.ABANDONED_UTTERANCE: DisfluencyType.ABANDONED,
                DisfluencyCategory.LEXICAL_SEARCH: DisfluencyType.LEXICAL_SEARCH,
                DisfluencyCategory.REPAIR_SUCCESS: DisfluencyType.REPAIR_SUCCESS,
                DisfluencyCategory.POSSIBLE_SOUND_REPETITION: DisfluencyType.REPETITION,
                DisfluencyCategory.POSSIBLE_PROLONGATION: DisfluencyType.PROLONGATION,
            }
            
            db_candidate = DisfluencyCandidate(
                id=cand.id,
                session_id=session_id,
                utterance_id=utterance_id,
                start_time=cand.start_time,
                end_time=cand.end_time,
                disfluency_type=type_mapping.get(cand.category, DisfluencyType.OTHER),
                evidence_text=cand.evidence_text,
                detector_source=cand.detector,
                confidence=cand.confidence,
                review_status=ReviewStatus.PENDING,
                metadata=cand.metadata
            )
            db_candidates.append(db_candidate)
        
        # Bulk insert
        if db_candidates:
            self.db.add_all(db_candidates)
            self.db.commit()
            for cand in db_candidates:
                self.db.refresh(cand)
        
        return db_candidates
    
    def review_candidate(
        self,
        candidate_id: str,
        status: ReviewStatus,
        reviewer: str,
        notes: Optional[str] = None
    ) -> DisfluencyCandidate:
        """Review and accept/reject a disfluency candidate."""
        candidate = self.db.query(DisfluencyCandidate).filter(
            DisfluencyCandidate.id == candidate_id
        ).first()
        
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")
        
        candidate.review_status = status
        candidate.reviewer = reviewer
        if notes:
            candidate.review_notes = notes
        candidate.reviewed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(candidate)
        
        return candidate
    
    def get_pending_candidates(self, session_id: str) -> list[DisfluencyCandidate]:
        """Get all pending candidates for a session."""
        return self.db.query(DisfluencyCandidate).filter(
            DisfluencyCandidate.session_id == session_id,
            DisfluencyCandidate.review_status == ReviewStatus.PENDING
        ).all()
    
    def get_accepted_candidates(self, session_id: str) -> list[DisfluencyCandidate]:
        """Get all accepted candidates for metrics computation."""
        return self.db.query(DisfluencyCandidate).filter(
            DisfluencyCandidate.session_id == session_id,
            DisfluencyCandidate.review_status == ReviewStatus.ACCEPTED
        ).all()
    
    def bulk_review(
        self,
        candidate_ids: list[str],
        status: ReviewStatus,
        reviewer: str
    ) -> int:
        """Bulk review multiple candidates."""
        count = self.db.query(DisfluencyCandidate).filter(
            DisfluencyCandidate.id.in_(candidate_ids)
        ).update({
            DisfluencyCandidate.review_status: status,
            DisfluencyCandidate.reviewer: reviewer,
            DisfluencyCandidate.reviewed_at: datetime.utcnow()
        }, synchronize_session=False)
        
        self.db.commit()
        return count
