import asyncio
import json
import signal
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from aio_pika.abc import AbstractIncomingMessage
from app.config.settings import settings
from app.model import ChatAsyncResponse, ChatRequest, ChatResponse, JobStatus
from app.service.queue_service import queue_service, QueueType
from app.utils.cache import redis_cache
from app.utils.logger import logger
from app.utils.retry import retry_policy


class BaseWorker(ABC):
    """Base class for specialized workers."""
    
    def __init__(self, queue_type: QueueType):
        self.queue_type: QueueType = queue_type
        self.is_running = False
        self.queue = queue_service
        self.cache = redis_cache
    
    async def start(self):
        """Start the worker."""
        logger.info(f"🚀 Starting {self.queue_type.upper()} Worker...")
        
        # Connect to services
        await self.cache.connect()
        await self.queue.connect()
        
        # Setup graceful shutdown
        self._setup_signal_handlers()
        
        self.is_running = True
        logger.info(f"✅ {self.queue_type.upper()} Worker ready to process messages")
        
        # Start consuming
        try:
            await self.queue.consume_queue(self.queue_type, self.process_message)
        except asyncio.CancelledError:
            logger.info(f"{self.queue_type.upper()} Worker consumption cancelled")
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown on SIGINT/SIGTERM."""
        import sys
        
        # Windows doesn't support signal handlers the same way as Unix
        # Use signal.signal() instead which works on both platforms
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
        
        # SIGTERM is not available on Windows, so only register what's available
        signal.signal(signal.SIGINT, signal_handler)
        
        if sys.platform != 'win32':
            signal.signal(signal.SIGTERM, signal_handler)
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info(f"🛑 Shutting down {self.queue_type.upper()} worker...")
        self.is_running = False
        
        await self.queue.disconnect()
        await self.cache.disconnect()
        
        logger.info(f"✅ {self.queue_type.upper()} Worker shutdown complete")
    
    async def process_message(self, message: AbstractIncomingMessage, queue_type: QueueType):
        """
        Process a message from the queue.
        Ensures proper ACK/NACK and status updates even on failures.
        """
        job_id = None
        idempotency_key = None
        should_reject = False
        
        try:
            # Parse message body
            try:
                body = json.loads(message.body.decode())
                job_id = body.get("job_id")
                request_data = body.get("request")
                idempotency_key = request_data.get("idempotency_key") if request_data else None
                target_mode = body.get("target_mode")
            except (json.JSONDecodeError, KeyError, AttributeError) as parse_error:
                logger.error(f"❌ [{self.queue_type.upper()}] Invalid message format: {parse_error}")
                # Invalid message format - reject without requeue
                should_reject = True
                raise
            
            logger.info(
                f"📨 [{self.queue_type.upper()}] Processing job {job_id} | "
                f"target_mode: {target_mode}"
            )
            
            # Validate message is for this worker
            if target_mode != self.queue_type:
                logger.warning(f"⚠️  Wrong queue. Job {job_id} routed to wrong worker")
                # Wrong queue - reject and requeue to correct queue
                should_reject = True
                return
            
            # Update job status to PROCESSING
            await self._update_job_status(
                job_id, 
                JobStatus.PROCESSING, 
                idempotency_key=idempotency_key
            )
            
            # Create ChatRequest from data
            chat_request = ChatRequest(**request_data)
            
            # Process with retry policy
            result = await self._process_with_retry(job_id, chat_request)
            
            # Update job status to COMPLETED
            await self._update_job_status(
                job_id, 
                JobStatus.COMPLETED, 
                result=result, 
                idempotency_key=idempotency_key
            )
            
            logger.info(f"✅ [{self.queue_type.upper()}] Job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(
                f"❌ [{self.queue_type.upper()}] Job {job_id or 'UNKNOWN'} failed: {e}", 
                exc_info=True
            )
            
            # Always try to update status to FAILED, even if job_id is unknown
            if job_id:
                try:
                    await self._update_job_status(
                        job_id, 
                        JobStatus.FAILED, 
                        error=str(e), 
                        idempotency_key=idempotency_key
                    )
                    logger.info(f"📝 Updated job {job_id} status to FAILED")
                except Exception as status_error:
                    logger.error(
                        f"⚠️  Failed to update FAILED status for job {job_id}: {status_error}",
                        exc_info=True
                    )
            
            # Don't requeue if we already marked as failed or if it's a parsing error
            should_reject = True
            raise
        
        finally:
            # Ensure message is acknowledged or rejected
            # Note: This is handled by aio_pika's context manager (async with message.process())
            # but we set should_reject flag for clarity
            pass

    
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
                mode=self.queue_type,
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
        error: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ):
        """Update job status in Redis and publish to response queue."""
        
        async_response = ChatAsyncResponse(
            job_id=job_id,
            status=status,
            idempotency_key=idempotency_key or job_id,
            result=result,
            error=error
        )
        
        cache_key = f"job:{job_id}"
        await self.cache.set(cache_key, async_response.model_dump(mode='json'), ttl=settings.JOB_TTL)
        await self.queue.publish_response(job_id, async_response)
