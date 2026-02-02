from fastapi import FastAPI
from app.controller.chat_controller import router as chat_router
from app.config.settings import settings
import uvicorn
import os
from dotenv import load_dotenv


load_dotenv()


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
    reload_flag = os.getenv("RELOAD", "False").lower() == "true"
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=reload_flag,
        log_level="info"
    )
