"""Audio ingestion service - validates, copies, and extracts metadata from audio files."""

import hashlib
import shutil
from pathlib import Path
from typing import Optional

import ffmpeg
from sqlalchemy.orm import Session as DBSession

from app.models import AudioFile, Session
from app.core.config import get_settings

settings = get_settings()


class IngestService:
    """Handles audio file ingestion, validation, and metadata extraction."""

    def __init__(self, db_session: DBSession):
        self.db = db_session

    def compute_content_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def extract_audio_metadata(self, file_path: Path) -> dict:
        """Extract codec, duration, sample rate, channels from audio file."""
        try:
            probe = ffmpeg.probe(str(file_path))
            audio_stream = next(
                (s for s in probe.get("streams", []) if s.get("codec_type") == "audio"),
                None,
            )
            if not audio_stream:
                raise ValueError("No audio stream found")

            return {
                "codec": audio_stream.get("codec_name", "unknown"),
                "duration_seconds": float(audio_stream.get("duration", 0)),
                "sample_rate": int(audio_stream.get("sample_rate", 0)),
                "channels": int(audio_stream.get("channels", 0)),
                "bit_rate": audio_stream.get("bit_rate"),
            }
        except ffmpeg.Error as e:
            raise ValueError(f"Failed to probe audio file: {e.stderr.decode() if e.stderr else str(e)}")

    def get_destination_path(
        self, course_id: str, session_id: str, original_filename: str
    ) -> Path:
        """Generate destination path for original audio file."""
        dest_dir = (
            settings.DATA_DIR / "audio" / course_id / session_id / "original"
        )
        dest_dir.mkdir(parents=True, exist_ok=True)
        base_name = Path(original_filename).stem
        extension = Path(original_filename).suffix or ".wav"
        dest_path = dest_dir / f"{base_name}{extension}"

        counter = 1
        while dest_path.exists():
            dest_path = dest_dir / f"{base_name}_{counter}{extension}"
            counter += 1

        return dest_path

    def ingest_file(
        self,
        source_path: Path,
        session: Session,
        role: str = "student",
        student_id: Optional[str] = None,
        original_filename: Optional[str] = None,
    ) -> AudioFile:
        """Ingest an audio file into the system."""
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        original_filename = original_filename or source_path.name
        metadata = self.extract_audio_metadata(source_path)
        content_hash = self.compute_content_hash(source_path)

        existing = (
            self.db.query(AudioFile)
            .filter(
                AudioFile.session_id == session.id,
                AudioFile.content_hash == content_hash,
            )
            .first()
        )
        if existing:
            return existing

        dest_path = self.get_destination_path(
            session.course_id, session.id, original_filename
        )
        shutil.copy2(source_path, dest_path)

        import os
        audio_file = AudioFile(
            session_id=session.id,
            original_filename=original_filename,
            stored_path=str(dest_path.relative_to(settings.DATA_DIR)),
            content_hash=content_hash,
            file_size_bytes=os.path.getsize(dest_path),
            duration_seconds=metadata["duration_seconds"],
            sample_rate=metadata["sample_rate"],
            channels=metadata["channels"],
            codec=metadata["codec"],
            import_source="manual_upload",
            is_processed=False,
        )

        self.db.add(audio_file)
        self.db.commit()
        self.db.refresh(audio_file)

        return audio_file

    def validate_audio_file(self, file_path: Path) -> tuple[bool, str]:
        """Validate that a file is a valid audio file."""
        if not file_path.exists():
            return False, "File does not exist"

        try:
            probe = ffmpeg.probe(str(file_path))
            has_audio = any(
                s.get("codec_type") == "audio" for s in probe.get("streams", [])
            )
            if not has_audio:
                return False, "File contains no audio stream"
            return True, ""
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            return False, f"Invalid or corrupt audio file: {error_msg}"

    def list_available_files(
        self, folder_path: Path, extensions: Optional[list[str]] = None
    ) -> list[Path]:
        """List audio files in a folder for import."""
        if extensions is None:
            extensions = [".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg", ".wma"]

        if not folder_path.exists():
            return []

        return [
            f for f in folder_path.iterdir()
            if f.is_file() and f.suffix.lower() in extensions
        ]
