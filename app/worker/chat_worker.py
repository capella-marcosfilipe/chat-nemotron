"""
Unified worker interface for job status checking.
This is used by the API to check job status.
"""
import json
from app.utils.cache import redis_cache
from app.model import ChatAsyncResponse, JobStatus


class ChatWorker:
    """Utility class for checking job status."""
    
    def __init__(self):
        self.cache = redis_cache
    
    async def get_job_status(self, job_id: str) -> ChatAsyncResponse:
        """Get job status from Redis."""
        cache_key = f"job:{job_id}"
        cached = await self.cache.get(cache_key)
        
        if cached:
            data = json.loads(cached) if isinstance(cached, str) else cached
            return ChatAsyncResponse(**data)
        
        # Job not found - assume pending
        return ChatAsyncResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            idempotency_key=job_id
        )
