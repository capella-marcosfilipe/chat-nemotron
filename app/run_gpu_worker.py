"""
Run GPU Worker.
Usage: python -m app.run_gpu_worker
"""
import asyncio
from app.worker.gpu_worker import main

if __name__ == "__main__":
    print("=" * 60)
    print("🎮 Nemotron GPU Worker Starting...")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("👋 GPU Worker stopped by user")
        print("=" * 60)
