import asyncio
import json
import signal
from datetime import datetime
from typing import Optional


from aio_pika.abc import AbstractIncomingMessage
from config.settings import settings
from engine.nemotron import nemotron_engine
from model import ChatAsyncResponse, ChatRequest, ChatResponse, JobStatus
from service.nemotron_service import nemotron_service
from service.queue_service import queue_service
from utils.cache import redis_cache
from utils.logger import logger
from utils.retry import retry_policy


class ChatWorker:
    """Worker to process chat requests from RabbitMQ queue."""
    
    def __init__(self):
        self.is_running = False
        self.nemotron = nemotron_service
        self.queue = queue_service
        self.cache = redis_cache
    
    async def start(self):
        """Start the worker."""
        logger.info("🚀 Starting Chat Worker...")
        
        # Connect to services
        await self.cache.connect()
        await self.queue.connect()
        
        # Setup graceful shutdown
        self._setup_signal_handlers()
        
        self.is_running = True
        logger.info("✅ Worker ready to process messages")
        
        # Start consuming
        try:
            await self.queue.consume_chat_requests(self.process_message)
        except asyncio.CancelledError:
            logger.info("Worker consumption cancelled")
    
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
        logger.info("🛑 Shutting down worker...")
        self.is_running = False
        
        await self.queue.disconnect()
        await self.cache.disconnect()
        
        logger.info("✅ Worker shutdown complete")
    
    async def process_message(self, message: AbstractIncomingMessage):
        """Process a single message from the queue."""
        job_id = None
        
        try:
            # Parse message
            body = json.loads(message.body.decode())
            job_id = body.get("job_id")
            request_data = body.get("request")
            
            logger.info(f"📨 Processing job {job_id}")
            
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
            
            logger.info(f"✅ Job {job_id} completed successfully")
        
        except Exception as e:
            logger.error(f"❌ Job {job_id} failed: {e}", exc_info=True)
            
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
            # Generate response
            response_text = await asyncio.to_thread(
                self.nemotron.generate_response,
                user_message=request.message,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                mode=None,  # Auto-detect
                use_reasoning=request.use_reasoning
            )
            
            # Calculate latency
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            
            mode = nemotron_engine.default_mode
            
            return ChatResponse(
                response=response_text,
                mode=mode,
                latency_ms=round(latency_ms, 2)
            )
        
        except Exception as e:
            logger.error(f"Error generating response for job {job_id}: {e}")
            raise
    

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
            idempotency_key=job_id,  # Use job_id as idempotency key
            result=result,
            error=error
        )
        
        # Store in Redis
        cache_key = f"job:{job_id}"
        await self.cache.set(
            cache_key,
            async_response.model_dump(mode='json'),
            ttl=settings.IDEMPOTENCY_TTL
        )
        
        # Publish to response queue
        await self.queue.publish_chat_response(job_id, async_response)
        
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


# Entry point for worker
async def main():
    """Main entry point for the worker."""
    worker = ChatWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
