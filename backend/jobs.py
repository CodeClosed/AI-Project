import time
import uuid
import logging
from typing import Dict, Any, Optional, List
from threading import Lock

logger = logging.getLogger(__name__)


class JobStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobManager:
    """Thread-safe background job state store with stage progression and auto-expiry."""

    def __init__(self, ttl_seconds: int = 3600):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()
        self.ttl_seconds = ttl_seconds

    def create_job(self, job_type: str = "menu_scan", user_id: Optional[int] = None) -> str:
        job_id = str(uuid.uuid4())
        with self.lock:
            self._cleanup_expired()
            self.jobs[job_id] = {
                "job_id": job_id,
                "job_type": job_type,
                "user_id": user_id,
                "status": JobStatus.PENDING,
                "progress": 10,
                "stage": "Validating & storing menu image...",
                "stages": [
                    {"id": "init", "label": "Validating & storing menu image", "status": "active"},
                    {"id": "ocr", "label": "Vision OCR & dish extraction", "status": "pending"},
                    {"id": "matrix", "label": "Clinical health matrix synthesis", "status": "pending"},
                    {"id": "recommend", "label": "3-tier safety scoring & plate optimization", "status": "pending"},
                ],
                "result": None,
                "error": None,
                "created_at": time.time(),
                "updated_at": time.time(),
            }
        return job_id

    def update_progress(self, job_id: str, progress: int, stage: str, stage_id: Optional[str] = None):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return
            job["status"] = JobStatus.PROCESSING
            job["progress"] = min(98, max(5, progress))
            job["stage"] = stage
            job["updated_at"] = time.time()
            if stage_id:
                for s in job["stages"]:
                    if s["id"] == stage_id:
                        s["status"] = "active"
                    elif s["status"] == "active" and s["id"] != stage_id:
                        s["status"] = "completed"

    def complete_job(self, job_id: str, result: Dict[str, Any]):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return
            job["status"] = JobStatus.COMPLETED
            job["progress"] = 100
            job["stage"] = "Analysis complete!"
            for s in job["stages"]:
                s["status"] = "completed"
            job["result"] = result
            job["updated_at"] = time.time()

    def fail_job(self, job_id: str, error_message: str):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return
            job["status"] = JobStatus.FAILED
            job["error"] = error_message
            job["stage"] = f"Failed: {error_message}"
            job["updated_at"] = time.time()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                return dict(job)
            return None

    def _cleanup_expired(self):
        now = time.time()
        expired = [jid for jid, j in self.jobs.items() if now - j["created_at"] > self.ttl_seconds]
        for jid in expired:
            del self.jobs[jid]


# Global singleton job manager
job_manager = JobManager()
