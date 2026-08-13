"""Session API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models import Session, SessionParticipant
from app.schemas import (
    SessionCreate, SessionResponse, SessionDetailResponse,
    SessionParticipantCreate, SessionParticipantResponse
)

router = APIRouter()


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(session: SessionCreate, db: Session = Depends(get_db)):
    """Create a new session."""
    db_session = Session(**session.model_dump())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


@router.get("/", response_model=List[SessionResponse])
def list_sessions(
    course_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List sessions, optionally filtered by course."""
    query = db.query(Session)
    if course_id:
        query = query.filter(Session.course_id == course_id)
    sessions = query.offset(skip).limit(limit).all()
    return sessions


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get a specific session with details."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/participants", response_model=SessionParticipantResponse)
def add_participant(
    session_id: int,
    participant: SessionParticipantCreate,
    db: Session = Depends(get_db)
):
    """Add a participant to a session."""
    # Verify session exists
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db_participant = SessionParticipant(
        session_id=session_id,
        student_id=participant.student_id,
        role=participant.role,
        track_number=participant.track_number,
        display_name=participant.display_name
    )
    db.add(db_participant)
    db.commit()
    db.refresh(db_participant)
    return db_participant


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    """Delete a session (cascades to audio files, jobs, etc.)."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    return None
