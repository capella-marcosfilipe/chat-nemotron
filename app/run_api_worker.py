"""
Run API Worker.
Usage: python -m app.run_api_worker
"""
import asyncio
from app.worker.api_worker import main

if __name__ == "__main__":
    print("=" * 60)
    print("🌐 Nemotron API Worker Starting...")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("👋 API Worker stopped by user")
        print("=" * 60)
