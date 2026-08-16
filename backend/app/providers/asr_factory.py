"""ASR provider factory and registry."""

from pathlib import Path
from typing import Optional, Type

from app.core.config import settings
from app.providers.asr_interface import ASRProvider, ASRResult


# Lazy imports to avoid loading heavy models unnecessarily
def get_asr_provider(
    provider_name: Optional[str] = None,
    model_size: Optional[str] = None,
    device: Optional[str] = None,
) -> ASRProvider:
    """
    Get ASR provider instance based on configuration.
    
    Args:
        provider_name: Provider name (whisper, faster-whisper, whisperx, crisperwhisper)
        model_size: Model size/name
        device: Compute device (cpu, cuda)
    
    Returns:
        Configured ASR provider instance
    
    Raises:
        ValueError: If provider is not supported or not installed
    """
    provider_name = provider_name or settings.asr_provider
    model_size = model_size or settings.asr_model
    device = device or ("cuda" if settings.gpu_enabled else "cpu")
    
    if provider_name == "whisper":
        from app.providers.asr_whisper import WhisperProvider
        return WhisperProvider(model_size=model_size, device=device)
    
    elif provider_name == "faster-whisper":
        try:
            from app.providers.asr_faster_whisper import FasterWhisperProvider
            return FasterWhisperProvider(model_size=model_size, device=device)
        except ImportError as e:
            raise ValueError(
                f"faster-whisper not installed. Install with: pip install faster-whisper. Error: {e}"
            )
    
    elif provider_name == "whisperx":
        try:
            from app.providers.asr_whisperx import WhisperXProvider
            return WhisperXProvider(model_size=model_size, device=device)
        except ImportError as e:
            raise ValueError(
                f"WhisperX not installed. Install following WhisperX documentation. Error: {e}"
            )
    
    elif provider_name == "crisperwhisper":
        try:
            from app.providers.asr_crisperwhisper import CrisperWhisperProvider
            return CrisperWhisperProvider(model_size=model_size, device=device)
        except ImportError as e:
            raise ValueError(
                f"crisperwhisper not installed. Error: {e}"
            )
    
    else:
        raise ValueError(f"Unsupported ASR provider: {provider_name}")


def transcribe_audio(
    audio_path: Path,
    provider_name: Optional[str] = None,
    language: Optional[str] = None,
    **kwargs
) -> ASRResult:
    """
    Convenience function to transcribe audio with configured provider.
    
    Args:
        audio_path: Path to audio file
        provider_name: Optional provider override
        language: Language code (defaults to config)
        **kwargs: Additional provider-specific options
    
    Returns:
        ASRResult with utterances and word timestamps
    """
    provider = get_asr_provider(provider_name)
    language = language or settings.asr_language
    return provider.transcribe(audio_path, language=language, **kwargs)
