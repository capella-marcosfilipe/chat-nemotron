from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from service.nemotron_service import nemotron_service
from model import ChatRequest, ChatResponse, SystemInfoResponse
from engine.nemotron import nemotron_engine, EngineMode
from typing import Optional


router = APIRouter(prefix="/chat", tags=["chat"])


# ========== Helper Functions ==========

def _create_stream_response(request: ChatRequest) -> StreamingResponse:
    """Create streaming response from request."""
    def generate():
        for chunk in nemotron_service.generate_response_stream(
            user_message=request.message,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            use_reasoning=request.use_reasoning
        ):
            yield chunk
    
    return StreamingResponse(generate(), media_type="text/plain")


def _generate_chat_response(
    request: ChatRequest,
    mode: Optional[EngineMode]
) -> ChatResponse:
    """Generate chat response with specified mode."""
    response_text = nemotron_service.generate_response(
        user_message=request.message,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
        mode=mode,
        use_reasoning=request.use_reasoning
    )
    
    actual_mode = mode if mode else nemotron_engine.default_mode
    return ChatResponse(response=response_text, mode=actual_mode)


def _validate_gpu_available():
    """Validate GPU is available, raise HTTPException if not."""
    if not nemotron_service.get_available_modes()["gpu"]:
        raise HTTPException(
            status_code=503,
            detail="GPU mode not available. CUDA not detected or model not loaded."
        )


# ========== Endpoints ==========

@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info():
    """Get available execution modes and system info.
    
    Example Response:
    {
        "available_modes": {"gpu": true, "api": true},
        "default_mode": "gpu"
    }
    """
    return SystemInfoResponse(
        available_modes=nemotron_service.get_available_modes(),
        default_mode=nemotron_engine.default_mode
    )


@router.post("/auto", response_model=ChatResponse)
async def chat_auto(request: ChatRequest):
    """
    Chat with automatic mode selection.
    Uses GPU if available, falls back to API.
    """
    try:
        if request.stream:
            return _create_stream_response(request)
        
        return _generate_chat_response(request, mode=None)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/gpu", response_model=ChatResponse)
async def chat_gpu(request: ChatRequest):
    """
    Chat using GPU only.
    Returns 503 if GPU is not available.
    """
    try:
        _validate_gpu_available()
        
        return _generate_chat_response(request, mode="gpu")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GPU error: {str(e)}")


@router.post("/api", response_model=ChatResponse)
async def chat_api(request: ChatRequest):
    """
    Chat using NVIDIA API only.
    Always available. Supports streaming and reasoning.
    """
    try:
        if request.stream:
            return _create_stream_response(request)
        
        return _generate_chat_response(request, mode="api")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")
