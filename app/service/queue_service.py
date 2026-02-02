import json
import uuid
from typing import Callable, Literal, Optional

from aio_pika import Message, connect_robust
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractQueue
from app.config.settings import settings
from app.model import ChatAsyncResponse, ChatRequest
from app.utils.logger import logger

QueueType = Literal["gpu", "api"]


class QueueService:
    """Async RabbitMQ service with separate queues per execution mode."""
    
    _instance: Optional['QueueService'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if QueueService._initialized:
            return
        
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        
        # Queues
        self.gpu_queue: Optional[AbstractQueue] = None
        self.api_queue: Optional[AbstractQueue] = None
        self.response_queue: Optional[AbstractQueue] = None
        self.gpu_dlq: Optional[AbstractQueue] = None
        self.api_dlq: Optional[AbstractQueue] = None
        
        QueueService._initialized = True
    
    async def connect(self):
        """Connect to RabbitMQ."""
        rabbitmq_url = (
            f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}"
            f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}{settings.RABBITMQ_VHOST}"
        )
        
        self.connection = await connect_robust(rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=settings.WORKER_PREFETCH_COUNT)
        
        await self._declare_queues()
        logger.info("RabbitMQ connected with separate GPU/API queues")
    
    async def _declare_queues(self):
        """Declare all queues with their respective DLQs."""
        
        # Dead Letter Queues
        if self.channel is None:
            raise RuntimeError("RabbitMQ channel is not initialized. Call connect() first.")

        self.gpu_dlq = await self.channel.declare_queue(
            settings.QUEUE_DLQ_GPU,
            durable=True
        )
        
        self.api_dlq = await self.channel.declare_queue(
            settings.QUEUE_DLQ_API,
            durable=True
        )
        
        # GPU Queue with DLX
        self.gpu_queue = await self.channel.declare_queue(
            settings.QUEUE_GPU_REQUESTS,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": settings.QUEUE_DLQ_GPU,
                "x-message-ttl": 600000  # 10 minutes
            }
        )
        
        # API Queue with DLX
        self.api_queue = await self.channel.declare_queue(
            settings.QUEUE_API_REQUESTS,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": settings.QUEUE_DLQ_API,
                "x-message-ttl": 600000  # 10 minutes
            }
        )
        
        # Response Queue
        self.response_queue = await self.channel.declare_queue(
            settings.QUEUE_RESPONSES,
            durable=True
        )
        
        logger.info("RabbitMQ queues declared: GPU, API, Responses, DLQs")
    
    async def disconnect(self):
        """Close RabbitMQ connection."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ disconnected")
    
    def _get_queue_name(self, mode: QueueType) -> str:
        """Get queue name based on execution mode."""
        if mode == "gpu":
            return settings.QUEUE_GPU_REQUESTS
        elif mode == "api":
            return settings.QUEUE_API_REQUESTS
        else:
            raise ValueError(f"Invalid queue type: {mode}")
    
    async def publish_chat_request(
        self, 
        request: ChatRequest,
        target_mode: QueueType
    ) -> str:
        """
        Publish chat request to specific queue.
        
        Args:
            request: Chat request
            target_mode: Which queue to send to ("gpu" or "api")
        
        Returns:
            job_id
        """
        job_id = str(uuid.uuid4())
        
        message_body = {
            "job_id": job_id,
            "request": request.model_dump(),
            "target_mode": target_mode
        }
        
        queue_name = self._get_queue_name(target_mode)
        
        message = Message(
            body=json.dumps(message_body).encode(),
            content_type="application/json",
            delivery_mode=2,  # Persistent
            priority=request.priority,
            message_id=job_id
        )
        
        if self.channel is None:
            raise RuntimeError("RabbitMQ channel is not initialized. Call connect() first.")

        await self.channel.default_exchange.publish(
            message,
            routing_key=queue_name
        )
        
        logger.info(
            f"Published job {job_id} to {target_mode.upper()} queue | "
            f"priority: {request.priority} | "
            f"idempotency_key: {request.idempotency_key}"
        )
        
        return job_id
    
    async def consume_queue(self, queue_type: QueueType, callback: Callable):
        """
        Consume messages from specific queue.
        
        Args:
            queue_type: Which queue to consume ("gpu" or "api")
            callback: Async function to process messages
        """
        if queue_type == "gpu":
            queue = self.gpu_queue
        elif queue_type == "api":
            queue = self.api_queue
        else:
            raise ValueError(f"Invalid queue type: {queue_type}")

        if queue is None:
            raise RuntimeError(f"{queue_type.upper()} queue is not initialized. Call connect() first.")

        logger.info(f"Starting to consume {queue_type.upper()} queue...")
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        await callback(message, queue_type)
                    except Exception as e:
                        logger.error(
                            f"Error processing {queue_type} message: {e}",
                            exc_info=True
                        )
                        raise
    
    async def publish_response(self, job_id: str, response: ChatAsyncResponse):
        """Publish chat response."""
        message_body = {
            "job_id": job_id,
            "response": response.model_dump(mode='json')
        }
        
        message = Message(
            body=json.dumps(message_body).encode(),
            content_type="application/json",
            delivery_mode=2,
            correlation_id=job_id
        )
        
        if self.channel is None:
            raise RuntimeError("RabbitMQ channel is not initialized. Call connect() first.")

        await self.channel.default_exchange.publish(
            message,
            routing_key=settings.QUEUE_RESPONSES
        )
        
        logger.info(f"Published response for job {job_id}")


# Global singleton instance
queue_service = QueueService()
