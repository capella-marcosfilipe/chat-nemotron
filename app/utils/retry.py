import asyncio
from typing import Callable, TypeVar, Type
from functools import wraps
from config.settings import settings
from model.error import ErrorCode
from utils.logger import logger

T = TypeVar('T')


class RetryPolicy:
    """Async retry policy with exponential backoff."""
    
    @staticmethod
    async def execute_with_retry(
        func: Callable[..., T],
        *args,
        max_retries: int = settings.MAX_RETRIES,
        base_delay: int = settings.RETRY_DELAY,
        backoff: int = settings.RETRY_BACKOFF,
        retry_on: tuple[Type[Exception], ...] = (Exception,),
        **kwargs
    ) -> T:
        """Execute async function with retry logic."""
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    return await result
                return result
            
            except retry_on as e:
                last_exception = e
                
                if attempt == max_retries:
                    logger.error(f"Max retries ({max_retries}) exceeded: {e}")
                    raise RuntimeError(f"{ErrorCode.MAX_RETRIES_EXCEEDED}: {str(e)}") from e
                
                delay = base_delay * (backoff ** attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
        
        if last_exception is not None:
            raise last_exception
        else:
            raise RuntimeError("Retry failed but no exception was captured.")
    
    @staticmethod
    def with_retry(
        max_retries: int = settings.MAX_RETRIES,
        base_delay: int = settings.RETRY_DELAY,
        backoff: int = settings.RETRY_BACKOFF,
        retry_on: tuple[Type[Exception], ...] = (Exception,)
    ):
        """Decorator for async retry logic."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await RetryPolicy.execute_with_retry(
                    func, *args,
                    max_retries=max_retries,
                    base_delay=base_delay,
                    backoff=backoff,
                    retry_on=retry_on,
                    **kwargs
                )
            return wrapper
        return decorator


retry_policy = RetryPolicy()
