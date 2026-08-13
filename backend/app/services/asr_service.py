"""ASR service for orchestrating transcription jobs."""

import time
from pathlib import Path
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.providers.asr_factory import get_asr_provider, transcribe_audio
from app.providers.asr_interface import ASRResult
from app.models import Transcript, Utterance, Word, AudioFile
from app.db.base import Base


class ASRService:
    """Service for running ASR transcription and storing results."""
    
    def __init__(self, db_session: Optional[DBSession] = None):
        self.db_session = db_session
    
    def transcribe_and_store(
        self,
        audio_file_id: int,
        provider_name: Optional[str] = None,
        model_size: Optional[str] = None,
        language: Optional[str] = None,
        store_raw_segments: bool = True,
    ) -> Transcript:
        """
        Transcribe audio file and store results in database.
        
        Args:
            audio_file_id: ID of AudioFile to transcribe
            provider_name: Override ASR provider
            model_size: Override model size
            language: Language code (defaults to config)
            store_raw_segments: Whether to store raw ASR segments in JSON
        
        Returns:
            Created Transcript record with utterances and words
        
        Raises:
            FileNotFoundError: If audio file not found
            RuntimeError: If ASR processing fails
        """
        if not self.db_session:
            raise RuntimeError("Database session required for storage")
        
        # Get audio file
        audio_file = self.db_session.query(AudioFile).get(audio_file_id)
        if not audio_file:
            raise FileNotFoundError(f"Audio file {audio_file_id} not found")
        
        audio_path = Path(audio_file.processed_path or audio_file.stored_path)
        if not audio_path.exists():
            # Try original path
            audio_path = Path(audio_file.stored_path)
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found at {audio_path}")
        
        # Get provider
        provider = get_asr_provider(provider_name, model_size)
        language = language or settings.asr.language
        
        # Transcribe
        start_time = time.time()
        asr_result = provider.transcribe(audio_path, language=language)
        processing_time = time.time() - start_time
        
        # Create transcript record
        transcript = Transcript(
            audio_file_id=audio_file_id,
            asr_provider=asr_result.provider,
            asr_model=asr_result.model,
            asr_language=asr_result.language,
            overall_confidence=asr_result.overall_confidence,
            word_level_confidence=any(
                w.confidence is not None
                for u in asr_result.utterances
                for w in u.words
            ) if asr_result.utterances else False,
            created_at=datetime.utcnow(),
            version=1,
            raw_segments=self._serialize_result(asr_result) if store_raw_segments else None,
        )
        self.db_session.add(transcript)
        self.db_session.flush()  # Get transcript ID
        
        # Create utterances and words
        for utt_seg in asr_result.utterances:
            utterance = Utterance(
                transcript_id=transcript.id,
                speaker_label="SPEAKER_0",  # Default, will be updated by diarization
                start_time=utt_seg.start_time,
                end_time=utt_seg.end_time,
                text=utt_seg.text,
                confidence=utt_seg.confidence,
                is_reviewed=False,
            )
            self.db_session.add(utterance)
            self.db_session.flush()
            
            # Create words
            for word_seg in utt_seg.words:
                word = Word(
                    utterance_id=utterance.id,
                    text=word_seg.text,
                    start_time=word_seg.start_time,
                    end_time=word_seg.end_time,
                    confidence=word_seg.confidence,
                )
                self.db_session.add(word)
        
        self.db_session.commit()
        self.db_session.refresh(transcript)
        
        return transcript
    
    def _serialize_result(self, result: ASRResult) -> dict:
        """Serialize ASR result to JSON-storable dict."""
        return {
            "provider": result.provider,
            "model": result.model,
            "language": result.language,
            "overall_confidence": result.overall_confidence,
            "processing_time_seconds": result.processing_time_seconds,
            "utterances": [
                {
                    "text": u.text,
                    "start_time": u.start_time,
                    "end_time": u.end_time,
                    "speaker_label": u.speaker_label,
                    "confidence": u.confidence,
                    "words": [
                        {
                            "text": w.text,
                            "start_time": w.start_time,
                            "end_time": w.end_time,
                            "confidence": w.confidence,
                        }
                        for w in u.words
                    ],
                }
                for u in result.utterances
            ],
            **result.metadata,
        }
