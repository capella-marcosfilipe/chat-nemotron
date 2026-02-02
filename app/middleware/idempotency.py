import json
from functools import wraps
from typing import Callable, Optional

from app.config.settings import settings
from app.model.error import ErrorContract
from app.utils.cache import redis_cache
from app.utils.logger import logger


class IdempotencyMiddleware:
    """Async idempotency middleware using Redis."""
    
    def __init__(self):
        self.cache = redis_cache
    
    def _generate_key(self, idempotency_key: str, endpoint: str) -> str:
        """Generate Redis key for idempotency."""
        return f"idempotency:{endpoint}:{idempotency_key}"
    
    async def get_cached_response(self, idempotency_key: str, endpoint: str) -> Optional[dict]:
        """Get cached response if exists."""
        key = self._generate_key(idempotency_key, endpoint)
        cached = await self.cache.get(key)
        
        if cached:
            logger.debug(f"Idempotency cache hit for key: {idempotency_key}")
            return json.loads(cached)
        return None
    
    async def cache_response(self, idempotency_key: str, endpoint: str, response: dict):
        """Cache response with TTL."""
        key = self._generate_key(idempotency_key, endpoint)
        await self.cache.set(key, response, ttl=settings.IDEMPOTENCY_TTL)
        logger.debug(f"Cached idempotent response for key: {idempotency_key}")
    
    async def is_processing(self, idempotency_key: str, endpoint: str) -> bool:
        """Check if request is currently being processed."""
        key = f"processing:{endpoint}:{idempotency_key}"
        return await self.cache.exists(key)
    
    async def mark_processing(self, idempotency_key: str, endpoint: str):
        """Mark request as processing."""
        key = f"processing:{endpoint}:{idempotency_key}"
        await self.cache.set(key, "1", ttl=300)  # 5 minutes lock
    
    async def unmark_processing(self, idempotency_key: str, endpoint: str):
        """Unmark request as processing."""
        key = f"processing:{endpoint}:{idempotency_key}"
        await self.cache.delete(key)
    
    def idempotent(self, endpoint: str):
        """Decorator for idempotent endpoints."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract idempotency_key from request
                request = kwargs.get('request') or (args[0] if args else None)
                
                if request is None or not hasattr(request, 'idempotency_key'):
                    return await func(*args, **kwargs)
                
                idempotency_key = request.idempotency_key
                
                # Check if already processed
                cached = await self.get_cached_response(idempotency_key, endpoint)
                if cached:
                    logger.info(f"Returning cached response for idempotency_key: {idempotency_key}")
                    return cached
                
                # Check if currently processing
                if await self.is_processing(idempotency_key, endpoint):
                    logger.warning(f"Request already processing: {idempotency_key}")
                    raise ValueError(ErrorContract.idempotency_conflict("Request is currently being processed"))
                
                # Mark as processing
                await self.mark_processing(idempotency_key, endpoint)
                
                try:
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    # Cache result
                    if isinstance(result, dict):
                        await self.cache_response(idempotency_key, endpoint, result)
                    
                    return result
                
                finally:
                    # Unmark processing
                    await self.unmark_processing(idempotency_key, endpoint)
            
            return wrapper
        return decorator


idempotency = IdempotencyMiddleware()
