from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChatResponse(BaseModel):
    response: str
    mode: str = Field(description="Execution mode (gpu or api)")
    latency_ms: Optional[float] = None


class ChatAsyncResponse(BaseModel):
    job_id: str
    status: JobStatus
    idempotency_key: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    result: Optional[ChatResponse] = None
    error: Optional[str] = None


class SystemInfoResponse(BaseModel):
    available_modes: dict[str, bool]
    default_mode: str


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
