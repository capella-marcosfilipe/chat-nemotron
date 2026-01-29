import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from controller.chat_controller import router as chat_router

load_dotenv()


app = FastAPI(
    title="Nemotron Chat API",
    description="Simple chat API using NVIDIA Nemotron",
    version="1.0.0"
)

app.include_router(chat_router)


@app.get("/")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "True").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
