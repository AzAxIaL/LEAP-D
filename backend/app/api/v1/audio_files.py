"""Audio file upload and management API endpoints."""

import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models import AudioFile, Session
from app.schemas import AudioFileResponse, AudioFileCreate
from app.services.ingest import IngestService
from app.services.preprocess import PreprocessService

router = APIRouter()


@router.post("/upload", response_model=AudioFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio_file(
    session_id: int = Form(...),
    file: UploadFile = File(...),
    track_number: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload an audio file for a session.
    
    The file is stored in the course/session/audio directory structure
    and metadata is recorded in the database.
    """
    # Verify session exists
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate file type
    allowed_types = [
        "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3",
        "audio/mp4", "audio/x-m4a", "audio/flac", "audio/ogg"
    ]
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: {allowed_types}"
        )
    
    # Use ingest service to store file
    ingest_service = IngestService()
    
    # Determine storage path based on session
    course_id = session.course_id
    storage_subpath = f"audio/{course_id}/{session_id}/original/{file.filename}"
    
    try:
        # Save file using ingest service
        saved_path = ingest_service.save_audio_file(
            file=file.file,
            filename=file.filename,
            subpath=storage_subpath,
        )
        
        # Extract metadata and validate
        preprocess_service = PreprocessService()
        validation = preprocess_service.validate_audio_file(Path(saved_path))
        
        if not validation["valid"]:
            # Clean up invalid file
            Path(saved_path).unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid audio file: {'; '.join(validation['errors'])}"
            )
        
        # Create database record
        metadata = validation["metadata"]
        audio_file = AudioFile(
            session_id=session_id,
            original_filename=file.filename,
            stored_path=saved_path,
            content_hash=metadata["content_hash"],
            file_size_bytes=metadata["file_size_bytes"],
            duration_seconds=metadata["duration_seconds"],
            sample_rate=metadata["sample_rate"],
            channels=metadata["channels"],
            codec=metadata["codec_name"],
            import_source="upload",
            is_processed=False,
        )
        db.add(audio_file)
        db.commit()
        db.refresh(audio_file)
        
        return audio_file
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{audio_file_id}", response_model=AudioFileResponse)
def get_audio_file(audio_file_id: int, db: Session = Depends(get_db)):
    """Get details of a specific audio file."""
    audio_file = db.query(AudioFile).filter(AudioFile.id == audio_file_id).first()
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    return audio_file


@router.delete("/{audio_file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_audio_file(audio_file_id: int, db: Session = Depends(get_db)):
    """
    Delete an audio file and its associated transcripts.
    
    This performs cascading deletion of related records.
    """
    audio_file = db.query(AudioFile).filter(AudioFile.id == audio_file_id).first()
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Delete physical file
    file_path = Path(audio_file.stored_path)
    if file_path.exists():
        file_path.unlink()
    
    # Delete processed file if exists
    if audio_file.processed_path:
        processed_path = Path(audio_file.processed_path)
        if processed_path.exists():
            processed_path.unlink()
    
    # Database record will be deleted by cascade
    db.delete(audio_file)
    db.commit()
    
    return None


@router.get("/session/{session_id}", response_model=List[AudioFileResponse])
def list_session_audio_files(session_id: int, db: Session = Depends(get_db)):
    """List all audio files for a session."""
    files = db.query(AudioFile).filter(AudioFile.session_id == session_id).all()
    return files
