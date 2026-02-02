from fastapi import APIRouter, HTTPException
from app.service.queue_service import queue_service, QueueType
from app.worker.chat_worker import ChatWorker
from app.model import ChatRequest, ChatAsyncResponse, SystemInfoResponse, ExecutionMode, JobStatus
from app.engine.nemotron import nemotron_engine
from app.service.nemotron_service import nemotron_service
from app.middleware.idempotency import idempotency
from app.utils.logger import logger


router = APIRouter(prefix="/chat", tags=["chat"])


# ========== Helper Functions ==========

async def _route_to_queue(request: ChatRequest) -> tuple[str, QueueType]:
    """
    Route request to appropriate queue based on mode.
    
    Returns:
        (job_id, target_queue)
    """
    # Ensure queue is connected
    if not queue_service.connection:
        await queue_service.connect()
    
    # Determine target queue
    if request.mode == ExecutionMode.GPU:
        # Force GPU queue
        if not nemotron_engine.cuda_available:
            raise HTTPException(
                status_code=503,
                detail="GPU mode requested but not available. Use /auto or /api instead."
            )
        target_mode: QueueType = "gpu"
    
    elif request.mode == ExecutionMode.API:
        # Force API queue
        target_mode: QueueType = "api"
    
    else:  # AUTO mode
        # Intelligent routing
        if nemotron_engine.cuda_available:
            target_mode: QueueType = "gpu"
            logger.info("AUTO mode: Routing to GPU queue")
        else:
            target_mode: QueueType = "api"
            logger.info("AUTO mode: Routing to API queue (GPU not available)")
    
    # Publish to queue
    job_id = await queue_service.publish_chat_request(request, target_mode)
    
    return job_id, target_mode


# ========== Endpoints ==========

@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info():
    """
    Get available execution modes and system info.
    """
    return SystemInfoResponse(
        available_modes=nemotron_service.get_available_modes(),
        default_mode=nemotron_engine.default_mode
    )


@router.post("/auto", response_model=ChatAsyncResponse)
@idempotency.idempotent("chat_auto")
async def chat_auto(request: ChatRequest):
    """
    **AUTO MODE**: Intelligent queue routing.
    
    - Automatically chooses GPU queue if available
    - Falls back to API queue if GPU unavailable
    - Returns immediately with job_id
    - Check status with GET /status/{job_id}
    """
    try:
        # Force AUTO mode
        request.mode = ExecutionMode.AUTO
        
        job_id, target_queue = await _route_to_queue(request)
        
        return ChatAsyncResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            idempotency_key=request.idempotency_key
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /auto: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/gpu", response_model=ChatAsyncResponse)
@idempotency.idempotent("chat_gpu")
async def chat_gpu(request: ChatRequest):
    """
    **GPU MODE**: Force GPU queue.
    
    - Sends request to GPU-specific queue
    - Returns 503 if GPU not available
    - Processed by GPU worker only
    - Returns immediately with job_id
    """
    try:
        # Force GPU mode
        request.mode = ExecutionMode.GPU
        
        job_id, target_queue = await _route_to_queue(request)
        
        return ChatAsyncResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            idempotency_key=request.idempotency_key
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /gpu: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/api", response_model=ChatAsyncResponse)
@idempotency.idempotent("chat_api")
async def chat_api(request: ChatRequest):
    """
    **API MODE**: Force API queue.
    
    - Sends request to API-specific queue
    - Always available
    - Supports reasoning tokens
    - Processed by API worker only
    - Returns immediately with job_id
    """
    try:
        # Force API mode
        request.mode = ExecutionMode.API
        
        job_id, target_queue = await _route_to_queue(request)
        
        return ChatAsyncResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            idempotency_key=request.idempotency_key
        )
    
    except Exception as e:
        logger.error(f"Error in /api: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/status/{job_id}", response_model=ChatAsyncResponse)
async def get_job_status(job_id: str):
    """
    Get status of any job (GPU or API queue).
    
    Status flow:
    - PENDING: Job in queue
    - PROCESSING: Worker processing
    - COMPLETED: Done (result available)
    - FAILED: Error (error message available)
    """
    try:
        worker = ChatWorker()
        result = await worker.get_job_status(job_id)
        return result
    
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
