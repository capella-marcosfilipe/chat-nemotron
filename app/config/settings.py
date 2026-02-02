from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API
    APP_NAME: str = "Nemotron Chat Service"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # NVIDIA API
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "your_default_api_key")
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # RabbitMQ
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"
    
    # Queue Names
    QUEUE_GPU_REQUESTS: str = "chat_gpu_requests"
    QUEUE_API_REQUESTS: str = "chat_api_requests"
    QUEUE_RESPONSES: str = "chat_responses"
    QUEUE_DLQ_GPU: str = "chat_gpu_dlq"
    QUEUE_DLQ_API: str = "chat_api_dlq"
    
    # Retry Policy
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2
    RETRY_BACKOFF: int = 2
    
    # Cache
    CACHE_TTL: int = 3600
    IDEMPOTENCY_TTL: int = 86400
    JOB_TTL: int = 86400  # 24h
    
    # Worker Settings
    WORKER_PREFETCH_COUNT: int = 1
    WORKER_GPU_INSTANCES: int = 1
    WORKER_API_INSTANCES: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
