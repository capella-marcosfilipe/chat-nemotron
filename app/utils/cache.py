import redis.asyncio as aioredis
import json
from typing import Optional, Any
from config.settings import settings
from utils.logger import logger


class RedisCache:
    """Async Redis cache singleton."""
    
    _instance: Optional['RedisCache'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if RedisCache._initialized:
            return
        
        self.client: Optional[aioredis.Redis] = None
        RedisCache._initialized = True
    
    async def connect(self):
        """Initialize Redis connection."""
        if self.client is None:
            self.client = await aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                password=settings.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Redis connected successfully")
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("Redis disconnected")
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        try:
            if self.client is None:
                logger.error("Redis client is not connected")
                return None
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with optional TTL."""
        try:
            if self.client is None:
                logger.error("Redis client is not connected")
                return
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if ttl:
                await self.client.setex(key, ttl, value)
            else:
                await self.client.set(key, value)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
    
    async def delete(self, key: str):
        """Delete key from cache."""
        try:
            if self.client is None:
                logger.error("Redis client is not connected")
                return
            await self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            if self.client is None:
                logger.error("Redis client is not connected")
                return False
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    async def incr(self, key: str) -> int:
        """Increment counter."""
        try:
            if self.client is None:
                logger.error("Redis client is not connected")
                return 0
            return await self.client.incr(key)
        except Exception as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return 0
    
    async def expire(self, key: str, ttl: int):
        """Set expiration on key."""
        try:
            if self.client is None:
                logger.error("Redis client is not connected")
                return
            await self.client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")


# Global singleton instance
redis_cache = RedisCache()
