"""Whisper ASR provider implementation."""

import time
from pathlib import Path
from typing import Optional

from app.providers.asr_interface import (
    ASRProvider,
    ASRResult,
    UtteranceSegment,
    WordSegment,
)


class WhisperProvider:
    """Whisper ASR provider using openai-whisper."""
    
    def __init__(self, model_size: str = "base", device: str = "cpu"):
        self.model_size = model_size
        self.device = device
        self._model = None
    
    @property
    def name(self) -> str:
        return "whisper"
    
    @property
    def supports_word_timestamps(self) -> bool:
        return True
    
    def _load_model(self):
        """Lazy-load Whisper model."""
        if self._model is None:
            try:
                import whisper
                self._model = whisper.load_model(
                    self.model_size,
                    device=self.device
                )
            except ImportError:
                raise RuntimeError(
                    "Whisper not installed. Install with: pip install openai-whisper"
                )
    
    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = "en",
        **kwargs
    ) -> ASRResult:
        """Transcribe audio using Whisper."""
        start_time = time.time()
        
        self._load_model()
        
        # Whisper options
        options = {
            "language": language,
            "word_timestamps": True,
            "verbose": False,
        }
        
        # Transcribe
        result = self._model.transcribe(str(audio_path), **options)
        
        # Parse segments
        utterances = []
        for segment in result.get("segments", []):
            words = []
            
            # Extract word-level timestamps if available
            if "words" in segment:
                for word_data in segment["words"]:
                    words.append(WordSegment(
                        text=word_data.get("text", ""),
                        start_time=word_data.get("start", 0.0),
                        end_time=word_data.get("end", 0.0),
                        confidence=word_data.get("confidence"),
                    ))
            
            utterances.append(UtteranceSegment(
                text=segment.get("text", "").strip(),
                start_time=segment.get("start", 0.0),
                end_time=segment.get("end", 0.0),
                confidence=segment.get("confidence"),
                words=words,
            ))
        
        processing_time = time.time() - start_time
        
        return ASRResult(
            utterances=utterances,
            provider=self.name,
            model=f"whisper-{self.model_size}",
            language=language or "en",
            overall_confidence=result.get("confidence"),
            processing_time_seconds=processing_time,
            metadata={
                "device": self.device,
                "segments_count": len(utterances),
            },
        )
