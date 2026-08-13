"""
Identity Resolution Service for LEAP-D Phase 2.

Combines diarization, voiceprint matching, and manual assignments
to produce final speaker identities for mixed audio files.

Implements:
- Multi-source identity fusion (track assignment, voiceprint, manual, diarization)
- Confidence-weighted resolution
- Conflict detection and safeguards
- Unknown label preservation (DIAR_*, UNKNOWN)
"""

import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class IdentityAssignment:
    """Final resolved identity for a speaker segment."""
    segment_id: str
    start: float
    end: float
    original_label: str  # From diarizer (e.g., "SPEAKER_0")
    assigned_student_id: Optional[int]
    assigned_student_name: Optional[str]
    confidence: float
    assignment_source: str  # "track", "voiceprint", "manual", "diarization"
    is_unknown: bool  # True if could not resolve to known student
    alternative_candidates: List[Dict[str, Any]]
    requires_review: bool


@dataclass
class IdentityResolutionResult:
    """Complete result of identity resolution for a session."""
    session_id: int
    audio_file_id: int
    total_segments: int
    matched_segments: int
    unknown_segments: int
    overlap_duration: float
    assignments: List[IdentityAssignment]
    resolution_metadata: Dict[str, Any]


class IdentityResolutionService:
    """
    Resolves speaker identities from multiple sources.
    
    Priority order:
    1. Manual assignment (teacher override)
    2. Track assignment (multi-track mode)
    3. Voiceprint match (with confidence threshold)
    4. Diarization-only label (UNKNOWN/DIAR_*)
    """

    def __init__(
        self,
        voiceprint_match_threshold: float = 0.65,
        require_consent_for_voiceprint: bool = True
    ):
        self.voiceprint_match_threshold = voiceprint_match_threshold
        self.require_consent = require_consent_for_voiceprint
        logger.info("IdentityResolutionService initialized")

    def resolve_identities(
        self,
        session_id: int,
        audio_file_id: int,
        diarized_segments: List[Dict[str, Any]],
        track_assignments: Optional[Dict[str, int]] = None,
        voiceprint_matches: Optional[List[Any]] = None,
        manual_assignments: Optional[Dict[str, int]] = None,
        student_names: Optional[Dict[int, str]] = None
    ) -> IdentityResolutionResult:
        """
        Resolve final speaker identities by fusing multiple sources.
        
        Args:
            session_id: Session identifier
            audio_file_id: Audio file identifier
            diarized_segments: Output from diarization service
            track_assignments: Map of track ID to student ID (multi-track mode)
            voiceprint_matches: Output from voiceprint matching service
            manual_assignments: Teacher overrides (segment_id -> student_id)
            student_names: Map of student_id -> name
            
        Returns:
            IdentityResolutionResult with resolved assignments
        """
        student_names = student_names or {}
        manual_assignments = manual_assignments or {}
        track_assignments = track_assignments or {}
        
        assignments = []
        matched_count = 0
        unknown_count = 0
        overlap_duration = 0.0
        
        # Track which students have been assigned (for one-to-one constraint)
        assigned_students: Set[int] = set()
        
        for i, seg in enumerate(diarized_segments):
            segment_id = seg.get("segment_id", f"seg_{i}")
            start = seg.get("start", 0.0)
            end = seg.get("end", 0.0)
            original_label = seg.get("speaker_label", "UNKNOWN")
            duration = end - start
            
            # Check for overlap
            if seg.get("overlap", False):
                overlap_duration += duration
            
            # Determine assignment source and student
            assigned_student_id = None
            assigned_student_name = None
            assignment_source = "diarization"
            confidence = seg.get("confidence", 0.5)
            requires_review = True
            alternatives = []
            
            # Priority 1: Manual assignment (highest priority)
            if segment_id in manual_assignments:
                assigned_student_id = manual_assignments[segment_id]
                assigned_student_name = student_names.get(assigned_student_id)
                assignment_source = "manual"
                confidence = 1.0
                requires_review = False
                logger.debug(f"Segment {segment_id}: manual assignment to student {assigned_student_id}")
            
            # Priority 2: Track assignment (multi-track mode)
            elif track_assignments:
                track_id = seg.get("track_id")
                if track_id and track_id in track_assignments:
                    assigned_student_id = track_assignments[track_id]
                    assigned_student_name = student_names.get(assigned_student_id)
                    assignment_source = "track"
                    confidence = 0.95
                    requires_review = False
                    logger.debug(f"Segment {segment_id}: track assignment to student {assigned_student_id}")
            
            # Priority 3: Voiceprint match
            elif voiceprint_matches:
                # Find matching result for this segment
                for match in voiceprint_matches:
                    if match.diarizer_label == original_label:
                        if match.student_id is not None and match.confidence >= self.voiceprint_match_threshold:
                            # Check one-to-one constraint
                            if match.student_id not in assigned_students:
                                assigned_student_id = match.student_id
                                assigned_student_name = match.student_name
                                assignment_source = "voiceprint"
                                confidence = match.confidence
                                requires_review = match.confidence < 0.85
                                alternatives = [
                                    {"student_id": sid, "confidence": conf}
                                    for sid, conf in match.alternative_matches
                                ]
                                logger.debug(
                                    f"Segment {segment_id}: voiceprint match to student "
                                    f"{assigned_student_id} (confidence: {confidence:.2f})"
                                )
                        break
            
            # Priority 4: Keep diarization label (unknown)
            if assigned_student_id is None:
                unknown_count += 1
                # Mark as unknown but preserve original label for display
                original_label = original_label if original_label.startswith("DIAR_") else f"DIAR_{original_label}"
            else:
                matched_count += 1
                assigned_students.add(assigned_student_id)
                requires_review = requires_review and assignment_source != "track"
            
            assignment = IdentityAssignment(
                segment_id=segment_id,
                start=start,
                end=end,
                original_label=original_label,
                assigned_student_id=assigned_student_id,
                assigned_student_name=assigned_student_name,
                confidence=confidence,
                assignment_source=assignment_source,
                is_unknown=assigned_student_id is None,
                alternative_candidates=alternatives,
                requires_review=requires_review
            )
            assignments.append(assignment)
        
        metadata = {
            "resolved_at": datetime.utcnow().isoformat(),
            "voiceprint_threshold": self.voiceprint_match_threshold,
            "sources_used": {
                "manual": bool(manual_assignments),
                "track": bool(track_assignments),
                "voiceprint": bool(voiceprint_matches),
                "diarization": True
            },
            "one_to_one_constraint_applied": True
        }
        
        result = IdentityResolutionResult(
            session_id=session_id,
            audio_file_id=audio_file_id,
            total_segments=len(assignments),
            matched_segments=matched_count,
            unknown_segments=unknown_count,
            overlap_duration=overlap_duration,
            assignments=assignments,
            resolution_metadata=metadata
        )
        
        logger.info(
            f"Identity resolution complete: {matched_count}/{len(assignments)} segments matched, "
            f"{unknown_count} unknown"
        )
        
        return result

    def update_manual_assignment(
        self,
        result: IdentityResolutionResult,
        segment_id: str,
        student_id: Optional[int],
        student_names: Dict[int, str]
    ) -> IdentityResolutionResult:
        """
        Update a single segment's assignment based on teacher correction.
        
        Creates a new result with the updated assignment while preserving
        the audit trail.
        """
        new_assignments = []
        
        for assignment in result.assignments:
            if assignment.segment_id == segment_id:
                new_assignment = IdentityAssignment(
                    segment_id=assignment.segment_id,
                    start=assignment.start,
                    end=assignment.end,
                    original_label=assignment.original_label,
                    assigned_student_id=student_id,
                    assigned_student_name=student_names.get(student_id) if student_id else None,
                    confidence=1.0 if student_id else 0.0,
                    assignment_source="manual" if student_id else "diarization",
                    is_unknown=student_id is None,
                    alternative_candidates=assignment.alternative_candidates,
                    requires_review=False
                )
                new_assignments.append(new_assignment)
            else:
                new_assignments.append(assignment)
        
        # Recalculate counts
        matched_count = sum(1 for a in new_assignments if a.assigned_student_id is not None)
        unknown_count = sum(1 for a in new_assignments if a.is_unknown)
        
        return IdentityResolutionResult(
            session_id=result.session_id,
            audio_file_id=result.audio_file_id,
            total_segments=len(new_assignments),
            matched_segments=matched_count,
            unknown_segments=unknown_count,
            overlap_duration=result.overlap_duration,
            assignments=new_assignments,
            resolution_metadata={
                **result.resolution_metadata,
                "last_manual_update": datetime.utcnow().isoformat()
            }
        )

    def get_confidence_summary(self, result: IdentityResolutionResult) -> Dict[str, Any]:
        """Generate summary statistics for resolution confidence."""
        if not result.assignments:
            return {"error": "No assignments"}
        
        confidences = [a.confidence for a in result.assignments]
        by_source = {}
        
        for assignment in result.assignments:
            source = assignment.assignment_source
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(assignment.confidence)
        
        summary = {
            "total_segments": result.total_segments,
            "mean_confidence": sum(confidences) / len(confidences),
            "min_confidence": min(confidences),
            "max_confidence": max(confidences),
            "segments_needing_review": sum(1 for a in result.assignments if a.requires_review),
            "by_assignment_source": {
                source: {
                    "count": len(confs),
                    "mean_confidence": sum(confs) / len(confs)
                }
                for source, confs in by_source.items()
            }
        }
        
        return summary
