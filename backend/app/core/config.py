"""
Application configuration and settings.
Uses pydantic-settings for environment-based configuration.
"""
from functools import lru_cache
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ASRSettings(BaseSettings):
    """ASR provider configuration."""
    provider: Literal["whisper", "faster-whisper", "whisperx", "crisperwhisper"] = Field(
        default="whisper",
        description="ASR provider to use"
    )
    model: str = Field(default="base", description="ASR model name/size")
    language: str = Field(default="en", description="Primary language code")
    compute_type: str = Field(default="float32", description="Compute precision")
    
    class Config:
        env_prefix = "ASR_"


class DiarizationSettings(BaseSettings):
    """Diarization provider configuration (Phase 2)."""
    provider: str = Field(default="pyannote", description="Diarization provider")
    model: str = Field(
        default="pyannote/speaker-diarization-3.1",
        description="Diarization model"
    )
    
    class Config:
        env_prefix = "DIARIZATION_"


class LLMSettings(BaseSettings):
    """LLM provider configuration."""
    provider: Literal["ollama", "openai", "anthropic"] = Field(
        default="ollama",
        description="LLM provider"
    )
    model: str = Field(default="llama3.1:8b", description="LLM model name")
    base_url: Optional[str] = Field(
        default="http://localhost:11434",
        description="LLM API base URL"
    )
    
    class Config:
        env_prefix = "LLM_"


class StorageSettings(BaseSettings):
    """Storage path configuration."""
    data_root: str = Field(default="./data", description="Root data directory")
    audio_path: str = Field(default="./data/audio", description="Audio storage")
    processed_path: str = Field(default="./data/processed", description="Processed files")
    voiceprints_path: str = Field(default="./data/voiceprints", description="Voiceprints")
    artifacts_path: str = Field(default="./data/artifacts", description="Job artifacts")
    reports_path: str = Field(default="./data/reports", description="Generated reports")
    
    class Config:
        env_prefix = ""
        env_file = ".env"


class ProcessingSettings(BaseSettings):
    """Audio processing configuration."""
    max_audio_duration_hours: int = Field(default=2, description="Maximum audio duration")
    max_session_duration_hours: int = Field(default=2, description="Maximum session duration")
    vad_min_speech_duration_ms: int = Field(default=250, description="VAD threshold")
    silence_trimming_enabled: bool = Field(default=False, description="Enable silence trimming")
    loudness_normalization_target: int = Field(
        default=-16,
        description="Loudness normalization target in LUFS"
    )
    ffmpeg_path: Optional[str] = Field(default=None, description="Path to FFmpeg binary")
    analysis_sample_rate: int = Field(default=16000, description="Analysis sample rate in Hz")
    
    class Config:
        env_prefix = ""


class IdentitySettings(BaseSettings):
    """Voiceprint identity matching thresholds (Phase 2)."""
    similarity_threshold: float = Field(default=0.75, ge=0, le=1)
    assign_threshold: float = Field(default=0.85, ge=0, le=1)
    one_to_one_matching_enabled: bool = Field(default=True)
    
    class Config:
        env_prefix = "VOICEPRINT_"


class DisfluencySettings(BaseSettings):
    """Disfluency detection configuration."""
    confidence_threshold: float = Field(default=0.6, ge=0, le=1)
    review_required_for_cefr: bool = Field(default=True)
    
    class Config:
        env_prefix = "DISFLUENCY_"


class PrivacySettings(BaseSettings):
    """Privacy and retention configuration."""
    default_retention_days: int = Field(default=365)
    consent_required_for_voiceprint: bool = Field(default=True)
    cloud_features_enabled: bool = Field(default=False)
    
    class Config:
        env_prefix = ""


class Settings(BaseSettings):
    """Main application settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Database
    database_url: str = Field(
        default="sqlite:///./data/efl_analysis.db",
        description="Database connection URL"
    )
    
    # GPU
    gpu_enabled: bool = Field(default=False, description="Enable GPU acceleration")
    cuda_device: int = Field(default=0, description="CUDA device ID")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Logging format")
    
    # Nested settings
    asr: ASRSettings = Field(default_factory=ASRSettings)
    diarization: DiarizationSettings = Field(default_factory=DiarizationSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    identity: IdentitySettings = Field(default_factory=IdentitySettings)
    disfluency: DisfluencySettings = Field(default_factory=DisfluencySettings)
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
    
    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return self.database_url.startswith("sqlite")
    
    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL database."""
        return self.database_url.startswith("postgresql")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance for convenience
settings = get_settings()
