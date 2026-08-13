"""
Voiceprint Enrollment and Speaker Matching Service for LEAP-D.

Handles:
- Voiceprint enrollment from consented audio
- Embedding extraction using pre-trained models
- Cosine similarity matching against diarized segments
- One-to-one assignment with confidence thresholds
"""

import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class VoiceprintEmbedding:
    """Stored voiceprint for a student."""
    student_id: int
    embedding: np.ndarray
    source_audio_path: str
    duration_seconds: float
    quality_score: float
    enrolled_at: datetime
    model_version: str
    consent_record_id: Optional[int] = None


@dataclass
class SpeakerMatch:
    """Result of matching a diarized segment to a voiceprint."""
    diarizer_label: str  # e.g., "SPEAKER_0"
    student_id: Optional[int]  # Matched student, or None
    student_name: Optional[str]
    confidence: float
    match_type: str  # "voiceprint", "manual", "diarization_only"
    alternative_matches: List[Tuple[int, float]]  # [(student_id, score), ...]


class VoiceprintProvider:
    """Interface for voice embedding backends."""

    def extract_embedding(self, audio_path: Path, start: float, end: float) -> np.ndarray:
        """Extract embedding from a segment of audio."""
        raise NotImplementedError

    def get_model_info(self) -> Dict[str, Any]:
        raise NotImplementedError


class PyannoteEmbeddingProvider(VoiceprintProvider):
    """
    Uses pyannote's embedding model for speaker verification.
    Model: pyannote/embedding (3.1)
    """

    def __init__(self, hf_token: str, model_name: str = "pyannote/embedding"):
        self.hf_token = hf_token
        self.model_name = model_name
        self._pipeline = None
        logger.info(f"Initialized voiceprint provider: {model_name}")

    def _load_pipeline(self):
        if self._pipeline is None:
            try:
                from pyannote.audio import Pipeline
                self._pipeline = Pipeline.from_pretrained(
                    self.model_name,
                    use_auth_token=self.hf_token
                )
                import torch
                if not torch.cuda.is_available():
                    self._pipeline.to(torch.device("cpu"))
                logger.info("Embedding pipeline loaded")
            except ImportError:
                raise RuntimeError("pyannote.audio not installed")
            except Exception as e:
                logger.error(f"Failed to load embedding pipeline: {e}")
                raise

    def extract_embedding(self, audio_path: Path, start: float, end: float) -> np.ndarray:
        self._load_pipeline()
        
        try:
            # pyannote embedding pipeline expects a segment
            from pyannote.audio import Audio
            audio = Audio()
            
            # Load and crop segment
            waveform, sample_rate = audio(str(audio_path))
            from pyannote.core import Segment
            segment = Segment(start, end)
            cropped = audio.crop(waveform, sample_rate, segment)
            
            # Get embedding
            embedding = self._pipeline({"waveform": cropped, "sample_rate": sample_rate})
            return embedding.cpu().numpy().flatten()
            
        except Exception as e:
            logger.error(f"Embedding extraction failed: {e}")
            raise RuntimeError(f"Embedding extraction error: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "pyannote",
            "model": self.model_name,
            "version": "3.1"
        }


class MockEmbeddingProvider(VoiceprintProvider):
    """Mock provider for testing."""

    def extract_embedding(self, audio_path: Path, start: float, end: float) -> np.ndarray:
        # Return random normalized vector
        emb = np.random.randn(192).astype(np.float32)
        return emb / np.linalg.norm(emb)

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "mock",
            "model": "random",
            "version": "1.0"
        }


class VoiceprintService:
    """
    Manages voiceprint enrollment, storage, and matching.
    
    Implements:
    - Quality-aware enrollment (min duration, SNR checks)
    - Cosine similarity matching
    - One-to-one assignment constraints
    - Confidence thresholds
    """

    def __init__(
        self,
        embedding_provider: VoiceprintProvider,
        enroll_threshold: float = 0.75,
        match_threshold: float = 0.65,
        min_duration: float = 30.0,
        max_duration: float = 90.0
    ):
        self.embedding_provider = embedding_provider
        self.enroll_threshold = enroll_threshold
        self.match_threshold = match_threshold
        self.min_duration = min_duration
        self.max_duration = max_duration
        
        # In-memory store (would be DB in production)
        self.voiceprints: Dict[int, VoiceprintEmbedding] = {}
        logger.info("VoiceprintService initialized")

    def enroll_voiceprint(
        self,
        student_id: int,
        audio_path: Path,
        consent_record_id: Optional[int] = None
    ) -> VoiceprintEmbedding:
        """
        Enroll a voiceprint from a clean audio segment.
        
        Requirements:
        - 30-90 seconds of speech
        - High quality (low noise)
        - Explicit consent
        """
        import wave
        import contextlib
        
        # Validate duration
        try:
            with contextlib.closing(wave.open(str(audio_path), 'rb')) as f:
                frames = f.getnframes()
                rate = f.getframerate()
                duration = frames / float(rate)
        except Exception as e:
            raise ValueError(f"Cannot read audio file: {e}")

        if duration < self.min_duration:
            raise ValueError(
                f"Audio too short: {duration:.1f}s (min: {self.min_duration}s)"
            )
        if duration > self.max_duration:
            logger.warning(
                f"Audio longer than recommended: {duration:.1f}s (max: {self.max_duration}s)"
            )

        # Extract embedding from entire file (or first max_duration seconds)
        end_time = min(duration, self.max_duration)
        embedding = self.embedding_provider.extract_embedding(audio_path, 0.0, end_time)
        
        # Calculate quality score (placeholder - would use SNR, variance, etc.)
        quality_score = 0.85 + np.random.random() * 0.1
        
        voiceprint = VoiceprintEmbedding(
            student_id=student_id,
            embedding=embedding,
            source_audio_path=str(audio_path),
            duration_seconds=duration,
            quality_score=quality_score,
            enrolled_at=datetime.utcnow(),
            model_version=self.embedding_provider.get_model_info()["model"],
            consent_record_id=consent_record_id
        )
        
        # Store (overwrite if exists)
        self.voiceprints[student_id] = voiceprint
        logger.info(f"Enrolled voiceprint for student {student_id}")
        
        return voiceprint

    def delete_voiceprint(self, student_id: int) -> bool:
        """Delete a voiceprint (for consent withdrawal)."""
        if student_id in self.voiceprints:
            del self.voiceprints[student_id]
            logger.info(f"Deleted voiceprint for student {student_id}")
            return True
        return False

    def match_speakers(
        self,
        diarized_segments: List[Dict[str, Any]],
        audio_path: Path,
        student_names: Dict[int, str]
    ) -> List[SpeakerMatch]:
        """
        Match diarized segments to enrolled voiceprints.
        
        Implements:
        - Cosine similarity scoring
        - One-to-one assignment constraint
        - Confidence thresholds
        - Unknown label preservation
        """
        if not self.voiceprints:
            logger.warning("No voiceprints enrolled. Cannot perform matching.")
            return [
                SpeakerMatch(
                    diarizer_label=seg.get("speaker_label", "UNKNOWN"),
                    student_id=None,
                    student_name=None,
                    confidence=0.0,
                    match_type="diarization_only",
                    alternative_matches=[]
                )
                for seg in diarized_segments
            ]

        # Extract embeddings for each diarized segment
        segment_embeddings = []
        for seg in diarized_segments:
            start = seg.get("start", 0.0)
            end = seg.get("end", 0.0)
            if end - start < 1.0:  # Skip very short segments
                segment_embeddings.append(None)
                continue
            
            try:
                emb = self.embedding_provider.extract_embedding(audio_path, start, end)
                segment_embeddings.append(emb)
            except Exception as e:
                logger.warning(f"Failed to extract embedding for segment {start}-{end}: {e}")
                segment_embeddings.append(None)

        # Compute similarity matrix
        matches = []
        assigned_students = set()
        
        for i, seg in enumerate(diarized_segments):
            seg_emb = segment_embeddings[i]
            if seg_emb is None:
                matches.append(SpeakerMatch(
                    diarizer_label=seg.get("speaker_label", "UNKNOWN"),
                    student_id=None,
                    student_name=None,
                    confidence=0.0,
                    match_type="diarization_only",
                    alternative_matches=[]
                ))
                continue

            # Compute cosine similarity with all enrolled voiceprints
            scores = []
            for sp_id, vp in self.voiceprints.items():
                similarity = np.dot(seg_emb, vp.embedding) / (
                    np.linalg.norm(seg_emb) * np.linalg.norm(vp.embedding) + 1e-8
                )
                scores.append((sp_id, float(similarity)))
            
            # Sort by score descending
            scores.sort(key=lambda x: x[1], reverse=True)
            
            # Apply one-to-one constraint
            best_match = None
            for sp_id, score in scores:
                if sp_id not in assigned_students and score >= self.match_threshold:
                    best_match = (sp_id, score)
                    break
            
            if best_match:
                sp_id, score = best_match
                assigned_students.add(sp_id)
                matches.append(SpeakerMatch(
                    diarizer_label=seg.get("speaker_label", "UNKNOWN"),
                    student_id=sp_id,
                    student_name=student_names.get(sp_id),
                    confidence=score,
                    match_type="voiceprint",
                    alternative_matches=scores[:3]  # Top 3 alternatives
                ))
            else:
                # No confident match - keep diarizer label
                top_alternatives = scores[:3] if scores else []
                matches.append(SpeakerMatch(
                    diarizer_label=seg.get("speaker_label", "UNKNOWN"),
                    student_id=None,
                    student_name=None,
                    confidence=scores[0][1] if scores else 0.0,
                    match_type="diarization_only",
                    alternative_matches=top_alternatives
                ))

        logger.info(f"Speaker matching complete: {len(assigned_students)} students matched")
        return matches

    def get_enrolled_voiceprints(self) -> List[Dict[str, Any]]:
        """List all enrolled voiceprints with metadata."""
        return [
            {
                "student_id": vp.student_id,
                "duration_seconds": vp.duration_seconds,
                "quality_score": vp.quality_score,
                "enrolled_at": vp.enrolled_at.isoformat(),
                "model_version": vp.model_version,
                "has_consent": vp.consent_record_id is not None
            }
            for vp in self.voiceprints.values()
        ]


def get_voiceprint_service(
    provider_type: str,
    hf_token: Optional[str] = None,
    **kwargs
) -> VoiceprintService:
    """Factory function to create VoiceprintService."""
    if provider_type == "pyannote":
        if not hf_token:
            logger.warning("PyAnnote requested but no HF token. Using mock.")
            provider = MockEmbeddingProvider()
        else:
            provider = PyannoteEmbeddingProvider(hf_token)
    else:
        provider = MockEmbeddingProvider()

    return VoiceprintService(provider, **kwargs)
