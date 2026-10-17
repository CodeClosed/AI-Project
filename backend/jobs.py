import time
import uuid
import json
import logging
from typing import Dict, Any, Optional, List
from threading import Lock

from backend.settings import settings

logger = logging.getLogger(__name__)


class JobStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobManager:
    """
    Background job state store with stage progression and auto-expiry.
    Supports optional Redis persistence with automatic in-memory fallback.
    """

    def __init__(self, ttl_seconds: int = 3600, redis_url: Optional[str] = None):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()
        self.ttl_seconds = ttl_seconds
        self.redis_client = None

        url = redis_url or settings.redis_url
        if url:
            try:
                import redis
                client = redis.from_url(url, decode_responses=True)
                client.ping()
                self.redis_client = client
                logger.info("JobManager connected to Redis distributed backend.")
            except Exception as e:
                logger.warning("Redis connection failed (%s); falling back to in-memory JobManager.", e)
                self.redis_client = None

    def _get_redis_key(self, job_id: str) -> str:
        return f"nutrimenu:job:{job_id}"

    def create_job(self, job_type: str = "menu_scan", user_id: Optional[int] = None) -> str:
        job_id = str(uuid.uuid4())
        job_payload = {
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

        if self.redis_client:
            try:
                rkey = self._get_redis_key(job_id)
                self.redis_client.setex(rkey, self.ttl_seconds, json.dumps(job_payload))
                return job_id
            except Exception as e:
                logger.warning("Redis setex error (%s); saving to in-memory fallback.", e)

        with self.lock:
            self._cleanup_expired()
            self.jobs[job_id] = job_payload
        return job_id

    def update_progress(self, job_id: str, progress: int, stage: str, stage_id: Optional[str] = None):
        if self.redis_client:
            try:
                rkey = self._get_redis_key(job_id)
                raw = self.redis_client.get(rkey)
                if raw:
                    job = json.loads(raw)
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
                    remaining_ttl = max(60, int(self.ttl_seconds - (time.time() - job["created_at"])))
                    self.redis_client.setex(rkey, remaining_ttl, json.dumps(job))
                    return
            except Exception as e:
                logger.warning("Redis update_progress error (%s); applying to in-memory fallback.", e)

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
        if self.redis_client:
            try:
                rkey = self._get_redis_key(job_id)
                raw = self.redis_client.get(rkey)
                if raw:
                    job = json.loads(raw)
                    job["status"] = JobStatus.COMPLETED
                    job["progress"] = 100
                    job["stage"] = "Analysis complete!"
                    for s in job["stages"]:
                        s["status"] = "completed"
                    job["result"] = result
                    job["updated_at"] = time.time()
                    remaining_ttl = max(60, int(self.ttl_seconds - (time.time() - job["created_at"])))
                    self.redis_client.setex(rkey, remaining_ttl, json.dumps(job))
                    return
            except Exception as e:
                logger.warning("Redis complete_job error (%s); applying to in-memory fallback.", e)

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
        if self.redis_client:
            try:
                rkey = self._get_redis_key(job_id)
                raw = self.redis_client.get(rkey)
                if raw:
                    job = json.loads(raw)
                    job["status"] = JobStatus.FAILED
                    job["error"] = error_message
                    job["stage"] = f"Failed: {error_message}"
                    job["updated_at"] = time.time()
                    remaining_ttl = max(60, int(self.ttl_seconds - (time.time() - job["created_at"])))
                    self.redis_client.setex(rkey, remaining_ttl, json.dumps(job))
                    return
            except Exception as e:
                logger.warning("Redis fail_job error (%s); applying to in-memory fallback.", e)

        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return
            job["status"] = JobStatus.FAILED
            job["error"] = error_message
            job["stage"] = f"Failed: {error_message}"
            job["updated_at"] = time.time()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        if self.redis_client:
            try:
                rkey = self._get_redis_key(job_id)
                raw = self.redis_client.get(rkey)
                if raw:
                    return json.loads(raw)
            except Exception as e:
                logger.warning("Redis get_job error (%s); querying in-memory fallback.", e)

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
