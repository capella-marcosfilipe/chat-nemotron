from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ExecutionMode(str, Enum):
    AUTO = "auto"
    GPU = "gpu"
    API = "api"


class ChatRequest(BaseModel):
    """Base chat request."""
    message: str = Field(..., min_length=1, description="User message")
    max_tokens: int = Field(default=512, ge=1, le=2048)
    temperature: float = Field(default=0.6, ge=0.0, le=1.0)
    use_reasoning: bool = Field(default=False, description="Enable reasoning tokens (API only)")
    
    # Async/Queue params
    idempotency_key: str = Field(..., description="Unique request identifier for idempotency")
    callback_url: Optional[str] = Field(None, description="Optional webhook callback URL")
    priority: int = Field(default=5, ge=1, le=10, description="Queue priority (1=lowest, 10=highest)")
    
    # Mode selection
    mode: ExecutionMode = Field(
        default=ExecutionMode.AUTO,
        description="Execution mode: auto (intelligent), gpu (force GPU), api (force API)"
    )
