import asyncio
import logging
import random
from typing import Callable, Any, Type, Tuple, Union

logger = logging.getLogger("company_intelligence.retry_manager")

class RetryManager:
    @staticmethod
    async def run_with_retry(
        func: Callable[[], Any],
        retries: int = 3,
        base_delay: float = 1.0,
        exponential: bool = True,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        context_name: str = "Operation"
    ) -> Any:
        """
        Execute an async function with optional exponential backoff and jitter.
        Specially handles different backoffs for typical failures like rate limits.
        """
        last_exception = None
        for attempt in range(1, retries + 1):
            try:
                return await func()
            except exceptions as e:
                last_exception = e
                # Check for rate-limiting patterns in the exception message
                err_msg = str(e).lower()
                is_rate_limit = "429" in err_msg or "too many requests" in err_msg or "rate limit" in err_msg
                
                # Double the backoff factor if we are hitting a rate limit
                delay_factor = 3.0 if is_rate_limit else 1.0
                
                if attempt == retries:
                    logger.error(f"{context_name} failed after {retries} attempts. Final error: {e}")
                    raise last_exception

                # Calculate delay with jitter
                delay = base_delay * (2 ** (attempt - 1)) if exponential else base_delay
                delay = (delay * delay_factor) + random.uniform(0, 0.5)
                
                logger.warning(
                    f"{context_name} failed on attempt {attempt}/{retries} due to: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                await asyncio.sleep(delay)
        
        if last_exception:
            raise last_exception
