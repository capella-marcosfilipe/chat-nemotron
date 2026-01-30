from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    max_tokens: int = Field(default=512, ge=1, le=2048)
    temperature: float = Field(default=0.6, ge=0.0, le=1.0)
    use_reasoning: bool = Field(default=False, description="Enable reasoning (API only)")
    stream: bool = Field(default=False, description="Enable streaming (API only)")


class ChatResponse(BaseModel):
    response: str
    mode: str = Field(description="Execution mode used (gpu or api)")
    