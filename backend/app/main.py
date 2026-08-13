"""
FastAPI application factory and main entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import get_settings
from app.db.base import init_db
from app.api.v1 import courses, students, sessions, jobs, audio_files

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="LEAP-D: Longitudinal ESL Assessment of Proficiency and Disfluency",
        description=(
            "Privacy-first, evidence-based platform for analyzing adult Japanese EFL "
            "learners' speaking proficiency with CEFR alignment. Supports multi-track "
            "review, transcript correction, disfluency analysis, and longitudinal progress tracking."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS middleware for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize database
    init_db()
    
    # Register routers
    app.include_router(courses.router, prefix="/api/v1/courses", tags=["courses"])
    app.include_router(students.router, prefix="/api/v1/students", tags=["students"])
    app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
    app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
    app.include_router(audio_files.router, prefix="/api/v1/audio-files", tags=["audio-files"])
    
    @app.get("/health")
    def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "0.1.0"}
    
    @app.get("/")
    def root():
        """Root endpoint with API information."""
        return {
            "name": "LEAP-D: Longitudinal ESL Assessment of Proficiency and Disfluency",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
        }
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
