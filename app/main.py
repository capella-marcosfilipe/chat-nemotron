from fastapi import FastAPI
from controller.chat_controller import router as chat_router
from config.settings import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Scalable chat API using NVIDIA Nemotron with async workers",
    version="1.0.0"
)

app.include_router(chat_router)


@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    import os
    
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "True").lower() == "true",
        log_level="info"
    )
