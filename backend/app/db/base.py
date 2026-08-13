"""
Database session management and base model.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator

from app.core.config import get_settings

settings = get_settings()

# Create engine with appropriate settings for SQLite or PostgreSQL
connect_args = {}
if settings.is_sqlite:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.log_level == "DEBUG",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    """
    Dependency that provides a database session.
    
    Yields:
        Session: SQLAlchemy database session
        
    Usage:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    # Import all models to register them with Base
    from app.models import (
        Course, Student, Consent, Session, SessionParticipant,
        AudioFile, Transcript, Utterance, Word, Job, JobStageResult,
        Voiceprint, DisfluencyCandidate, Assessment, AssessmentEvidence,
        Report, PronunciationCandidate, InteractionPair
    )
    
    Base.metadata.create_all(bind=engine)
