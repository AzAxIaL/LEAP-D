"""Job orchestration service for background processing.

Provides:
- Persistent job state with stages
- Structured logs and progress tracking
- Cancellation and retry policy
- Idempotent stages with per-stage artifacts
- Resource management (GPU/CPU, model loading)
"""

import json
import logging
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Job, JobStatus, JobStage, JobStageResult


logger = logging.getLogger(__name__)


class StageType(str, Enum):
    """Types of processing stages."""
    INGEST = "ingest"
    PREPROCESS = "preprocess"
    ASR = "asr"
    ALIGNMENT = "alignment"
    DIARIZATION = "diarization"
    IDENTITY = "identity"
    TRANSCRIPT = "transcript"
    DISFLUENCY = "disfluency"
    FLUENCY_METRICS = "fluency_metrics"
    PRONUNCIATION = "pronunciation"
    INTERACTION = "interaction"
    ASSESSMENT = "assessment"
    REPORTS = "reports"


class JobOrchestrator:
    """Manages background job execution with stages and resource control."""
    
    def __init__(self, db_session: Session, max_concurrent_jobs: int = 1):
        self.db = db_session
        self.max_concurrent_jobs = max_concurrent_jobs
        self._stage_handlers: dict[StageType, Callable] = {}
        self._running_jobs: dict[str, dict] = {}
    
    def register_stage_handler(
        self,
        stage_type: StageType,
        handler: Callable[[str, dict], dict]
    ):
        """Register a handler function for a stage type."""
        self._stage_handlers[stage_type] = handler
    
    def create_job(
        self,
        session_id: str,
        stages: list[StageType],
        created_by: str = "system",
        priority: int = 0
    ) -> Job:
        """Create a new multi-stage job."""
        job_id = str(uuid4())
        
        job = Job(
            id=job_id,
            session_id=session_id,
            status=JobStatus.QUEUED,
            created_by=created_by,
            priority=priority,
            total_stages=len(stages),
            completed_stages=0
        )
        
        # Create stage records in order
        for idx, stage_type in enumerate(stages):
            stage = JobStage(
                id=str(uuid4()),
                job_id=job_id,
                stage_type=stage_type.value,
                stage_order=idx,
                status=JobStatus.QUEUED
            )
            self.db.add(stage)
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Created job {job_id} with {len(stages)} stages")
        return job
    
    def execute_job(self, job_id: str) -> dict:
        """Execute all stages of a job sequentially."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.status == JobStatus.CANCELLED:
            return {"status": "cancelled", "reason": "Job was cancelled before execution"}
        
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        self.db.commit()
        
        self._running_jobs[job_id] = {
            "started_at": datetime.utcnow(),
            "current_stage": None,
            "logs": []
        }
        
        try:
            # Get stages in order
            stages = self.db.query(JobStage).filter(
                JobStage.job_id == job_id
            ).order_by(JobStage.stage_order).all()
            
            results = []
            for stage in stages:
                if job.status == JobStatus.CANCELLED:
                    logger.info(f"Job {job_id} cancelled at stage {stage.stage_type}")
                    break
                
                stage_result = self._execute_stage(job, stage)
                results.append(stage_result)
                
                if stage_result["status"] == "failed":
                    job.status = JobStatus.FAILED
                    job.error_message = stage_result.get("error", "Unknown error")
                    break
                
                job.completed_stages += 1
            
            if job.status != JobStatus.FAILED:
                if job.status == JobStatus.CANCELLED:
                    job.status = JobStatus.CANCELLED
                else:
                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.utcnow()
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            logger.exception(f"Job {job_id} failed with exception")
        
        finally:
            if job.status not in [JobStatus.RUNNING, JobStatus.QUEUED]:
                job.finished_at = datetime.utcnow()
            
            self.db.commit()
            self._running_jobs.pop(job_id, None)
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "completed_stages": job.completed_stages,
            "total_stages": job.total_stages,
            "results": results
        }
    
    def _execute_stage(self, job: Job, stage: JobStage) -> dict:
        """Execute a single job stage."""
        stage.status = JobStatus.RUNNING
        stage.started_at = datetime.utcnow()
        self.db.commit()
        
        self._running_jobs[job.id]["current_stage"] = stage.stage_type
        self._log_progress(job.id, f"Starting stage: {stage.stage_type}")
        
        handler = self._stage_handlers.get(StageType(stage.stage_type))
        
        if not handler:
            result = {
                "stage": stage.stage_type,
                "status": "failed",
                "error": f"No handler registered for stage type: {stage.stage_type}"
            }
        else:
            try:
                # Execute handler
                context = {
                    "job_id": job.id,
                    "session_id": job.session_id,
                    "stage_id": stage.id,
                    "previous_results": self._get_previous_results(job.id, stage.stage_order)
                }
                
                result_data = handler(job.session_id, context)
                
                result = {
                    "stage": stage.stage_type,
                    "status": "success",
                    "data": result_data,
                    "artifacts": self._store_artifacts(job.id, stage.id, result_data)
                }
                
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                logger.exception(f"Stage {stage.stage_type} failed")
                result = {
                    "stage": stage.stage_type,
                    "status": "failed",
                    "error": error_msg,
                    "traceback": traceback.format_exc()
                }
        
        # Update stage record
        stage.status = JobStatus(result["status"])
        stage.finished_at = datetime.utcnow()
        stage.result = json.dumps(result)
        
        # Store result metadata
        stage_result = JobStageResult(
            id=str(uuid4()),
            stage_id=stage.id,
            result_type=result["status"],
            result_data=json.dumps(result.get("data", {})),
            artifacts_path=json.dumps(result.get("artifacts", {}))
        )
        self.db.add(stage_result)
        self.db.commit()
        
        self._log_progress(
            job.id,
            f"Completed stage: {stage.stage_type} - {result['status']}"
        )
        
        return result
    
    def _get_previous_results(self, job_id: str, current_order: int) -> list[dict]:
        """Get results from previous stages."""
        stages = self.db.query(JobStage).filter(
            JobStage.job_id == job_id,
            JobStage.stage_order < current_order
        ).order_by(JobStage.stage_order).all()
        
        results = []
        for stage in stages:
            if stage.result:
                try:
                    result = json.loads(stage.result)
                    if result.get("status") == "success":
                        results.append({
                            "stage": stage.stage_type,
                            "data": result.get("data", {})
                        })
                except json.JSONDecodeError:
                    pass
        
        return results
    
    def _store_artifacts(
        self,
        job_id: str,
        stage_id: str,
        result_data: dict
    ) -> dict:
        """Store stage artifacts to disk."""
        from app.core.config import settings
        
        artifacts_dir = Path(settings.data_dir) / "artifacts" / job_id / stage_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        stored_paths = {}
        
        # Store JSON data
        if result_data:
            data_file = artifacts_dir / "result.json"
            with open(data_file, "w") as f:
                json.dump(result_data, f, indent=2, default=str)
            stored_paths["result_json"] = str(data_file)
        
        return stored_paths
    
    def _log_progress(self, job_id: str, message: str):
        """Log progress message for a job."""
        if job_id in self._running_jobs:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "message": message
            }
            self._running_jobs[job_id]["logs"].append(log_entry)
            logger.info(f"Job {job_id}: {message}")
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running or queued job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return False
        
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False
        
        job.status = JobStatus.CANCELLED
        job.cancelled_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Cancelled job {job_id}")
        return True
    
    def retry_job(self, job_id: str) -> Optional[Job]:
        """Retry a failed job from the beginning."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        
        if job.status != JobStatus.FAILED:
            logger.warning(f"Cannot retry job {job_id} with status {job.status}")
            return None
        
        # Reset job state
        job.status = JobStatus.QUEUED
        job.completed_stages = 0
        job.started_at = None
        job.finished_at = None
        job.error_message = None
        
        # Reset all stages
        stages = self.db.query(JobStage).filter(
            JobStage.job_id == job_id
        ).all()
        
        for stage in stages:
            stage.status = JobStatus.QUEUED
            stage.started_at = None
            stage.finished_at = None
            stage.result = None
        
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Retrying job {job_id}")
        return job
    
    def get_job_status(self, job_id: str) -> dict:
        """Get detailed job status including stage progress."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        stages = self.db.query(JobStage).filter(
            JobStage.job_id == job_id
        ).order_by(JobStage.stage_order).all()
        
        stage_details = []
        for stage in stages:
            stage_info = {
                "stage_id": stage.id,
                "stage_type": stage.stage_type,
                "stage_order": stage.stage_order,
                "status": stage.status.value if stage.status else None,
                "started_at": stage.started_at.isoformat() if stage.started_at else None,
                "finished_at": stage.finished_at.isoformat() if stage.finished_at else None
            }
            
            # Add result summary if available
            if stage.result:
                try:
                    result = json.loads(stage.result)
                    stage_info["result_summary"] = {
                        "status": result.get("status"),
                        "error": result.get("error")
                    }
                except json.JSONDecodeError:
                    pass
            
            stage_details.append(stage_info)
        
        # Get runtime logs if job is running
        logs = []
        if job_id in self._running_jobs:
            logs = self._running_jobs[job_id]["logs"]
        
        return {
            "job_id": job.id,
            "session_id": job.session_id,
            "status": job.status.value,
            "priority": job.priority,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "completed_stages": job.completed_stages,
            "total_stages": job.total_stages,
            "error_message": job.error_message,
            "stages": stage_details,
            "logs": logs
        }
    
    def get_queue_status(self) -> dict:
        """Get status of all jobs in queue."""
        queued = self.db.query(Job).filter(
            Job.status == JobStatus.QUEUED
        ).order_by(Job.priority.desc(), Job.created_at).all()
        
        running = self.db.query(Job).filter(
            Job.status == JobStatus.RUNNING
        ).all()
        
        return {
            "queued_count": len(queued),
            "running_count": len(running),
            "max_concurrent": self.max_concurrent_jobs,
            "queued_jobs": [
                {"job_id": j.id, "session_id": j.session_id, "priority": j.priority}
                for j in queued
            ],
            "running_jobs": [
                {"job_id": j.id, "session_id": j.session_id, "started_at": j.started_at.isoformat() if j.started_at else None}
                for j in running
            ]
        }


# Default orchestrator instance (will be initialized per-request in production)
_default_orchestrator: Optional[JobOrchestrator] = None


def get_orchestrator(db_session: Session) -> JobOrchestrator:
    """Get or create the default job orchestrator."""
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = JobOrchestrator(db_session)
    return _default_orchestrator
