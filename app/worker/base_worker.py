"""Base worker class with common functionality."""
import asyncio
import json
import signal
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from aio_pika.abc import AbstractIncomingMessage
from config.settings import settings
from model import ChatAsyncResponse, ChatRequest, ChatResponse, JobStatus
from service.queue_service import QueueType, queue_service
from utils.cache import redis_cache
from utils.logger import logger
from utils.retry import retry_policy


class BaseWorker(ABC):
    """Base class for all workers."""
    
    def __init__(self, worker_type: QueueType):
        self.worker_type = worker_type
        self.is_running = False
        self.queue = queue_service
        self.cache = redis_cache
    
    async def start(self):
        """Start the worker."""
        logger.info(f"🚀 Starting {self.worker_type.upper()} Worker...")
        
        # Connect to services
        await self.cache.connect()
        await self.queue.connect()
        
        # Setup graceful shutdown
        self._setup_signal_handlers()
        
        self.is_running = True
        logger.info(f"✅ {self.worker_type.upper()} Worker ready")
        
        # Start consuming
        try:
            await self.queue.consume_queue(self.worker_type, self.process_message)
        except asyncio.CancelledError:
            logger.info(f"{self.worker_type.upper()} Worker consumption cancelled")
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown on SIGINT/SIGTERM."""
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self.shutdown())
            )
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info(f"🛑 Shutting down {self.worker_type.upper()} worker...")
        self.is_running = False
        
        await self.queue.disconnect()
        await self.cache.disconnect()
        
        logger.info(f"✅ {self.worker_type.upper()} Worker shutdown complete")
    
    async def process_message(self, message: AbstractIncomingMessage, queue_type: QueueType):
        """Process a single message from the queue."""
        job_id = None
        
        try:
            # Parse message
            body = json.loads(message.body.decode())
            job_id = body.get("job_id")
            request_data = body.get("request")
            target_mode = body.get("target_mode")
            
            logger.info(
                f"📨 [{self.worker_type.upper()}] Processing job {job_id} | "
                f"target_mode: {target_mode}"
            )
            
            # Validate message is for this worker
            if target_mode != self.worker_type:
                logger.warning(
                    f"⚠️  Job {job_id} target_mode={target_mode} but received by "
                    f"{self.worker_type} worker. Skipping."
                )
                return
            
            # Update job status to PROCESSING
            await self._update_job_status(job_id, JobStatus.PROCESSING)
            
            # Create ChatRequest from data
            chat_request = ChatRequest(**request_data)
            
            # Process with retry policy
            result = await self._process_with_retry(job_id, chat_request)
            
            # Update job status to COMPLETED
            await self._update_job_status(
                job_id, 
                JobStatus.COMPLETED,
                result=result
            )
            
            logger.info(f"✅ [{self.worker_type.upper()}] Job {job_id} completed")
        
        except Exception as e:
            logger.error(
                f"❌ [{self.worker_type.upper()}] Job {job_id} failed: {e}",
                exc_info=True
            )
            
            # Update job status to FAILED
            if job_id:
                await self._update_job_status(
                    job_id,
                    JobStatus.FAILED,
                    error=str(e)
                )
    
    @retry_policy.with_retry(
        max_retries=settings.MAX_RETRIES,
        base_delay=settings.RETRY_DELAY,
        backoff=settings.RETRY_BACKOFF
    )
    async def _process_with_retry(self, job_id: str, request: ChatRequest) -> ChatResponse:
        """Process chat request with retry logic."""
        start_time = datetime.now()
        
        try:
            # Call specialized processing method
            response_text = await self.generate_response(request)
            
            # Calculate latency
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            return ChatResponse(
                response=response_text,
                mode=self.worker_type,
                latency_ms=round(latency_ms, 2)
            )
        
        except Exception as e:
            logger.error(f"Error generating response for job {job_id}: {e}")
            raise
    
    @abstractmethod
    async def generate_response(self, request: ChatRequest) -> str:
        """
        Generate response - must be implemented by subclasses.
        
        Args:
            request: Chat request
            
        Returns:
            Generated response text
        """
        pass
    
    async def _update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        result: Optional[ChatResponse] = None,
        error: Optional[str] = None
    ):
        """Update job status in Redis and publish to response queue."""
        
        # Create response object
        async_response = ChatAsyncResponse(
            job_id=job_id,
            status=status,
            idempotency_key=job_id,
            result=result,
            error=error
        )
        
        # Store in Redis
        cache_key = f"job:{job_id}"
        await self.cache.set(
            cache_key,
            async_response.model_dump(mode='json'),
            ttl=settings.JOB_TTL
        )
        
        # Publish to response queue
        await self.queue.publish_response(job_id, async_response)
        
        logger.debug(f"Updated job {job_id} status to {status}")
    
    async def get_job_status(self, job_id: str) -> ChatAsyncResponse:
        """Get job status from Redis."""
        cache_key = f"job:{job_id}"
        cached = await self.cache.get(cache_key)
        
        if cached:
            data = json.loads(cached) if isinstance(cached, str) else cached
            return ChatAsyncResponse(**data)
        
        # Job not found
        return ChatAsyncResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            idempotency_key=job_id
        )
