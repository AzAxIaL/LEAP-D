"""API endpoints for disfluency management."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ReviewStatus
from app.schemas.disfluency import (
    DisfluencyCandidateResponse,
    DisfluencyReviewRequest,
    DisfluencyBulkReviewRequest,
    DisfluencyMetricsResponse
)
from app.services.disfluency import DisfluencyService
from app.services.fluency_metrics import FluencyMetricsService


router = APIRouter()


@router.get("/sessions/{session_id}/disfluencies", response_model=list[DisfluencyCandidateResponse])
def list_disfluency_candidates(
    session_id: str,
    status: Optional[ReviewStatus] = Query(None, description="Filter by review status"),
    db: Session = Depends(get_db)
):
    """List disfluency candidates for a session."""
    service = DisfluencyService(db)
    
    if status == ReviewStatus.PENDING:
        candidates = service.get_pending_candidates(session_id)
    elif status == ReviewStatus.ACCEPTED:
        candidates = service.get_accepted_candidates(session_id)
    else:
        # Get all candidates
        from app.models import DisfluencyCandidate
        candidates = db.query(DisfluencyCandidate).filter(
            DisfluencyCandidate.session_id == session_id
        ).all()
    
    return [
        DisfluencyCandidateResponse(
            id=c.id,
            session_id=c.session_id,
            utterance_id=c.utterance_id,
            start_time=c.start_time,
            end_time=c.end_time,
            disfluency_type=c.disfluency_type,
            evidence_text=c.evidence_text,
            detector_source=c.detector_source,
            confidence=c.confidence,
            review_status=c.review_status,
            reviewer=c.reviewer,
            review_notes=c.review_notes,
            reviewed_at=c.reviewed_at,
            metadata=c.metadata
        )
        for c in candidates
    ]


@router.put("/disfluencies/{candidate_id}/review", response_model=DisfluencyCandidateResponse)
def review_disfluency_candidate(
    candidate_id: str,
    review_request: DisfluencyReviewRequest,
    db: Session = Depends(get_db)
):
    """Review and accept/reject a disfluency candidate."""
    service = DisfluencyService(db)
    
    try:
        candidate = service.review_candidate(
            candidate_id=candidate_id,
            status=review_request.status,
            reviewer=review_request.reviewer,
            notes=review_request.notes
        )
        
        return DisfluencyCandidateResponse(
            id=candidate.id,
            session_id=candidate.session_id,
            utterance_id=candidate.utterance_id,
            start_time=candidate.start_time,
            end_time=candidate.end_time,
            disfluency_type=candidate.disfluency_type,
            evidence_text=candidate.evidence_text,
            detector_source=candidate.detector_source,
            confidence=candidate.confidence,
            review_status=candidate.review_status,
            reviewer=candidate.reviewer,
            review_notes=candidate.review_notes,
            reviewed_at=candidate.reviewed_at,
            metadata=candidate.metadata
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/disfluencies/bulk-review")
def bulk_review_disfluencies(
    request: DisfluencyBulkReviewRequest,
    db: Session = Depends(get_db)
):
    """Bulk review multiple disfluency candidates."""
    service = DisfluencyService(db)
    
    count = service.bulk_review(
        candidate_ids=request.candidate_ids,
        status=request.status,
        reviewer=request.reviewer
    )
    
    return {"updated_count": count, "status": request.status.value}


@router.get("/sessions/{session_id}/students/{student_id}/fluency-metrics", response_model=DisfluencyMetricsResponse)
def get_fluency_metrics(
    session_id: str,
    student_id: str,
    db: Session = Depends(get_db)
):
    """Get computed fluency metrics for a student session."""
    metrics_service = FluencyMetricsService(db)
    
    metrics = metrics_service.compute_metrics(student_id, session_id)
    
    return DisfluencyMetricsResponse(**metrics.to_dict())


@router.get("/sessions/{session_id}/fluency-metrics/aggregated")
def get_session_aggregate_metrics(session_id: str, db: Session = Depends(get_db)):
    """Get aggregated fluency metrics for all students in a session."""
    metrics_service = FluencyMetricsService(db)
    
    aggregate = metrics_service.compute_session_aggregate(session_id)
    
    return aggregate
