from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from service.nemotron_service import nemotron_service


router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    max_tokens: int = Field(default=512, ge=1, le=2048)
    temperature: float = Field(default=0.6, ge=0.0, le=1.0)
    use_reasoning: bool = Field(default=False, description="Enable reasoning tokens")
    stream: bool = Field(default=False, description="Enable streaming response")


class ChatResponse(BaseModel):
    response: str
    

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message and get a response from Nemotron.
    Supports both streaming and non-streaming modes.
    """
    try:
        if request.stream:
            # Streaming response
            def generate():
                for chunk in nemotron_service.generate_response_stream(
                    user_message=request.message,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    use_reasoning=request.use_reasoning
                ):
                    yield chunk
            
            return StreamingResponse(generate(), media_type="text/plain")
        else:
            # Non-streaming response
            response_text = nemotron_service.generate_response(
                user_message=request.message,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                use_reasoning=request.use_reasoning
            )
            return ChatResponse(response=response_text)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
