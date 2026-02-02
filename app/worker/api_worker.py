import asyncio
import debugpy

from app.model import ChatRequest
from app.service.nemotron_service import nemotron_service
from app.utils.logger import logger
from app.worker.base_worker import BaseWorker


DEBUG_PORT = 49123
debugpy.listen(("0.0.0.0", DEBUG_PORT))
print(f"🔍 Debugger is listening on 0.0.0.0:{DEBUG_PORT}")


class APIWorker(BaseWorker):
    """Worker that processes requests using NVIDIA API."""
    
    def __init__(self):
        super().__init__(queue_type="api")
        self.nemotron = nemotron_service
    
    async def start(self):
        """Start API worker."""
        logger.info("🌐 API Worker using NVIDIA API endpoint")
        await super().start()
    
    async def generate_response(self, request: ChatRequest) -> str:
        """Generate response using NVIDIA API."""
        logger.debug(
            f"[API] Generating response | "
            f"message: {request.message[:50]}... | "
            f"max_tokens: {request.max_tokens} | "
            f"reasoning: {request.use_reasoning}"
        )
        
        # Run in thread to not block event loop
        response = await asyncio.to_thread(
            self.nemotron.generate_response,
            user_message=request.message,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            mode="api",
            use_reasoning=request.use_reasoning
        )
        
        logger.debug(f"[API] Generation complete: {len(response)} chars")
        return response


async def main():
    """Main entry point for API worker."""
    worker = APIWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
