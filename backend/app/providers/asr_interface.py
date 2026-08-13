"""ASR provider interface and implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol


@dataclass
class WordSegment:
    """Word-level transcript segment with timing."""
    text: str
    start_time: float
    end_time: float
    confidence: Optional[float] = None


@dataclass
class UtteranceSegment:
    """Utterance-level transcript segment."""
    text: str
    start_time: float
    end_time: float
    speaker_label: Optional[str] = None
    confidence: Optional[float] = None
    words: list[WordSegment] = field(default_factory=list)


@dataclass
class ASRResult:
    """Complete ASR transcription result."""
    utterances: list[UtteranceSegment]
    provider: str
    model: str
    language: str
    overall_confidence: Optional[float] = None
    processing_time_seconds: Optional[float] = None
    metadata: dict = field(default_factory=dict)


class ASRProvider(Protocol):
    """Protocol for ASR providers."""
    
    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        **kwargs
    ) -> ASRResult:
        """Transcribe audio file to text with word timestamps."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        pass
    
    @property
    @abstractmethod
    def supports_word_timestamps(self) -> bool:
        """Whether provider supports word-level timestamps."""
        pass
