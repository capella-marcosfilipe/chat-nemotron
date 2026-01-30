"""
Dedicated script to run the chat worker.
Usage: python -m app.run_worker
"""
import asyncio
from worker.chat_worker import main

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 Nemotron Chat Worker Starting...")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("👋 Worker stopped by user")
        print("=" * 60)
