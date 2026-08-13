"""Preprocessing service for audio validation, conversion, and normalization."""

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class AudioMetadata:
    """Extracted audio metadata."""
    duration_seconds: float
    sample_rate: int
    channels: int
    codec_name: str
    bit_rate: Optional[int]
    content_hash: str
    original_filename: str


class PreprocessService:
    """Audio preprocessing using FFmpeg."""
    
    def __init__(self):
        self.ffmpeg_path = settings.ffmpeg_path
    
    def _run_ffprobe(self, input_path: Path) -> dict:
        """Extract metadata using ffprobe."""
        cmd = [
            self.ffmpeg_path or "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(input_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")
        return json.loads(result.stdout)
    
    def _compute_content_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def extract_metadata(self, audio_path: Path) -> AudioMetadata:
        """Extract comprehensive metadata from audio file."""
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        probe_data = self._run_ffprobe(audio_path)
        
        # Get format info
        format_info = probe_data.get("format", {})
        duration = float(format_info.get("duration", 0))
        bit_rate = int(format_info.get("bit_rate")) if format_info.get("bit_rate") else None
        
        # Get stream info (prefer audio stream)
        audio_stream = None
        for stream in probe_data.get("streams", []):
            if stream.get("codec_type") == "audio":
                audio_stream = stream
                break
        
        if not audio_stream:
            raise ValueError("No audio stream found in file")
        
        sample_rate = int(audio_stream.get("sample_rate", 0))
        channels = int(audio_stream.get("channels", 0))
        codec_name = audio_stream.get("codec_name", "unknown")
        
        content_hash = self._compute_content_hash(audio_path)
        
        return AudioMetadata(
            duration_seconds=duration,
            sample_rate=sample_rate,
            channels=channels,
            codec_name=codec_name,
            bit_rate=bit_rate,
            content_hash=content_hash,
            original_filename=audio_path.name
        )
    
    def convert_to_analysis_format(
        self,
        input_path: Path,
        output_path: Path,
        target_sample_rate: int = 16000,
        normalize_loudness: bool = False,
        trim_silence: bool = False
    ) -> dict:
        """
        Convert audio to analysis-ready format.
        
        Returns timing map if silence trimming is enabled.
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build FFmpeg command
        cmd = [self.ffmpeg_path or "ffmpeg", "-y", "-i", str(input_path)]
        
        # Audio filters
        filters = []
        
        if normalize_loudness:
            # EBU R128 loudness normalization to -16 LUFS
            filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
        
        if trim_silence:
            # Note: This requires post-processing to compute timing map
            filters.append("silenceremove=start_periods=1:start_threshold=-50dB:detection=peak")
        
        if filters:
            cmd.extend(["-af", ",".join(filters)])
        
        # Output format: 16kHz mono WAV
        cmd.extend([
            "-ar", str(target_sample_rate),
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(output_path)
        ])
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")
        
        # Compute timing map if silence was trimmed
        timing_map = None
        if trim_silence:
            timing_map = self._compute_silence_timing_map(input_path, output_path)
        
        return {
            "output_path": str(output_path),
            "timing_map": timing_map,
            "normalized": normalize_loudness,
            "trimmed": trim_silence
        }
    
    def _compute_silence_timing_map(
        self,
        original_path: Path,
        processed_path: Path
    ) -> list[dict]:
        """
        Compute mapping from processed timestamps to original timestamps.
        
        Uses FFmpeg silencedetect to find silence regions in original,
        then computes cumulative offset.
        """
        cmd = [
            self.ffmpeg_path or "ffmpeg",
            "-i", str(original_path),
            "-af", "silencedetect=noise=-50dB:d=0.3",
            "-f", "null",
            "-"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        stderr_output = result.stderr
        
        # Parse silence regions
        silence_regions = []
        for line in stderr_output.split("\n"):
            if "silence_start:" in line or "silence_end:" in line:
                # Extract timestamp
                parts = line.split("silence_")[1].split(":")
                if len(parts) >= 2:
                    try:
                        timestamp = float(parts[1].strip())
                        silence_regions.append({
                            "type": "start" if "start" in line else "end",
                            "time": timestamp
                        })
                    except ValueError:
                        continue
        
        # Build timing map (simplified - just return offset pairs)
        timing_map = []
        cumulative_offset = 0.0
        current_original_time = 0.0
        
        for region in silence_regions:
            if region["type"] == "start":
                # Map current processed time to original time
                timing_map.append({
                    "processed_time": current_original_time - cumulative_offset,
                    "original_time": current_original_time
                })
            else:
                # Silence ended, update cumulative offset
                cumulative_offset = region["time"] - current_original_time
                current_original_time = region["time"]
        
        return timing_map
    
    def validate_audio_file(self, audio_path: Path) -> dict:
        """
        Validate audio file for processing.
        
        Returns validation result with actionable errors.
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "metadata": None
        }
        
        try:
            metadata = self.extract_metadata(audio_path)
            result["metadata"] = {
                "duration_seconds": metadata.duration_seconds,
                "sample_rate": metadata.sample_rate,
                "channels": metadata.channels,
                "codec_name": metadata.codec_name,
                "file_size_bytes": audio_path.stat().st_size,
                "content_hash": metadata.content_hash
            }
            
            # Check duration limits
            if metadata.duration_seconds < 1.0:
                result["errors"].append("Audio too short (< 1 second)")
                result["valid"] = False
            
            if metadata.duration_seconds > settings.max_session_duration_hours * 3600:
                max_hours = settings.max_session_duration_hours
                result["errors"].append(f"Audio exceeds maximum duration ({max_hours} hours)")
                result["valid"] = False
            
            # Check for corrupt files
            if metadata.codec_name == "unknown":
                result["warnings"].append("Unknown codec - may have compatibility issues")
                
        except FileNotFoundError as e:
            result["valid"] = False
            result["errors"].append(str(e))
        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Failed to read audio file: {str(e)}")
        
        return result
    
    def detect_corruption(self, audio_path: Path) -> bool:
        """Detect if audio file is corrupted or unreadable."""
        try:
            cmd = [
                self.ffmpeg_path or "ffmpeg",
                "-v", "error",
                "-i", str(audio_path),
                "-f", "null",
                "-"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return result.returncode != 0
        except Exception:
            return True
