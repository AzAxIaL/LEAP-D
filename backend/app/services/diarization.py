"""
Speaker Diarization Service for LEAP-D.

Handles speaker segmentation for mixed audio files using pyannote.audio.
Produces time-aligned speaker turns with confidence scores.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import timedelta

logger = logging.getLogger(__name__)


@dataclass
class SpeakerTurn:
    """Represents a single speaker turn from diarization."""
    start: float  # seconds
    end: float    # seconds
    speaker_label: str  # e.g., "SPEAKER_0", "DIAR_1"
    confidence: float
    overlap: bool = False
    track_index: int = 0  # For multi-speaker overlap scenarios


class DiarizationProvider:
    """Interface for diarization backends."""

    def process(self, audio_path: Path, num_speakers: Optional[int] = None) -> List[SpeakerTurn]:
        raise NotImplementedError

    def get_model_info(self) -> Dict[str, Any]:
        raise NotImplementedError


class PyAnnoteDiarizationProvider(DiarizationProvider):
    """
    PyAnnote-based diarization implementation.
    
    Requires HuggingFace token for gated models (pyannote/speaker-diarization-3.1).
    Handles GPU/CPU fallback and memory management.
    """

    def __init__(self, hf_token: str, model_name: str = "pyannote/speaker-diarization-3.1"):
        self.hf_token = hf_token
        self.model_name = model_name
        self._pipeline = None
        logger.info(f"Initialized PyAnnote provider with model: {model_name}")

    def _load_pipeline(self):
        """Lazy load the pipeline to manage memory."""
        if self._pipeline is None:
            try:
                from pyannote.audio import Pipeline
                self._pipeline = Pipeline.from_pretrained(
                    self.model_name,
                    use_auth_token=self.hf_token
                )
                # Configure for CPU if GPU not available
                import torch
                if not torch.cuda.is_available():
                    self._pipeline.to(torch.device("cpu"))
                logger.info("Diarization pipeline loaded successfully")
            except ImportError:
                raise RuntimeError("pyannote.audio not installed. Run: pip install pyannote.audio")
            except Exception as e:
                logger.error(f"Failed to load diarization pipeline: {e}")
                raise

    def process(self, audio_path: Path, num_speakers: Optional[int] = None) -> List[SpeakerTurn]:
        """
        Run diarization on an audio file.
        
        Args:
            audio_path: Path to the audio file (WAV preferred)
            num_speakers: Optional hint for number of speakers
            
        Returns:
            List of SpeakerTurn objects sorted by start time
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self._load_pipeline()
        
        try:
            # Apply pipeline
            diarization = self._pipeline(str(audio_path))
            
            turns = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speaker_turn = SpeakerTurn(
                    start=turn.start,
                    end=turn.end,
                    speaker_label=speaker,
                    confidence=0.85,  # Placeholder; pyannote 3.x doesn't always expose per-turn confidence
                    overlap=False  # Would need separate overlap detection
                )
                turns.append(speaker_turn)
            
            # Sort by start time
            turns.sort(key=lambda t: t.start)
            logger.info(f"Diarization complete: {len(turns)} turns found")
            return turns
            
        except Exception as e:
            logger.error(f"Diarization failed for {audio_path}: {e}")
            raise RuntimeError(f"Diarization processing error: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "pyannote",
            "model": self.model_name,
            "version": "3.1",
            "hf_token_configured": bool(self.hf_token)
        }


class MockDiarizationProvider(DiarizationProvider):
    """
    Mock provider for testing without pyannote dependency.
    Generates synthetic speaker turns based on audio duration.
    """

    def __init__(self):
        logger.info("Initialized Mock Diarization Provider")

    def process(self, audio_path: Path, num_speakers: Optional[int] = None) -> List[SpeakerTurn]:
        import wave
        import contextlib
        
        # Get duration
        try:
            with contextlib.closing(wave.open(str(audio_path), 'rb')) as f:
                frames = f.getnframes()
                rate = f.getframerate()
                duration = frames / float(rate)
        except Exception:
            duration = 60.0  # Fallback
            
        turns = []
        speaker_count = num_speakers or 2
        segment_length = 5.0  # Seconds per segment
        
        current_time = 0.0
        speaker_idx = 0
        
        while current_time < duration:
            end_time = min(current_time + segment_length, duration)
            turns.append(SpeakerTurn(
                start=current_time,
                end=end_time,
                speaker_label=f"SPEAKER_{speaker_idx}",
                confidence=0.95
            ))
            current_time = end_time
            speaker_idx = (speaker_idx + 1) % speaker_count
            
        return turns

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "mock",
            "model": "synthetic",
            "version": "1.0"
        }


def get_diarization_provider(provider_type: str, hf_token: Optional[str] = None) -> DiarizationProvider:
    """Factory function to get diarization provider."""
    if provider_type == "pyannote":
        if not hf_token:
            logger.warning("PyAnnote requested but no HF token provided. Falling back to mock.")
            return MockDiarizationProvider()
        return PyAnnoteDiarizationProvider(hf_token)
    elif provider_type == "mock":
        return MockDiarizationProvider()
    else:
        logger.warning(f"Unknown diarization provider '{provider_type}'. Using mock.")
        return MockDiarizationProvider()
