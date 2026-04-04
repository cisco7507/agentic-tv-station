"""
Retry decorator for MCP tools to ensure reliable execution with exponential backoff.
"""

import time
import functools
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

def retry_with_backoff(max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """
    Decorator that retries a function with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (including first try)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_attempts - 1:  # Last attempt
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay:.2f}s...")
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        return wrapper
    return decorator

def retry_on_failure(max_attempts: int = 3):
    """
    Simple retry decorator that retries on any exception.
    """
    return retry_with_backoff(max_attempts=max_attempts)
