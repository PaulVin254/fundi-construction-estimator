# =============================================================================
# FILE: retry_config.py
# PURPOSE:
#   Provides retry logic with exponential backoff for API calls and operations.
#   Ensures robust error handling and graceful degradation.
# =============================================================================

import time
import functools
from typing import Callable, Any, Optional, Tuple, Type
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# RETRY CONFIGURATION
# =============================================================================

class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        timeout: Optional[float] = 300.0,  # 5 minutes default
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before first retry
            max_delay: Maximum delay in seconds between retries
            exponential_base: Base for exponential backoff calculation
            timeout: Maximum total time in seconds for all attempts
            retryable_exceptions: Tuple of exception types that should trigger retry
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.timeout = timeout
        self.retryable_exceptions = retryable_exceptions
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt using exponential backoff.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = self.initial_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


# =============================================================================
# DEFAULT CONFIGURATIONS
# =============================================================================

# Configuration for API calls (Gemini, etc.)
API_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    timeout=300.0,  # 5 minutes
    retryable_exceptions=(
        ConnectionError,
        TimeoutError,
        Exception,  # Catch-all for API errors
    )
)

# Configuration for file operations
FILE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=0.5,
    max_delay=5.0,
    exponential_base=2.0,
    timeout=30.0,
    retryable_exceptions=(IOError, OSError, PermissionError)
)

# Configuration for network operations
NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=4,
    initial_delay=2.0,
    max_delay=60.0,
    exponential_base=2.5,
    timeout=180.0,
    retryable_exceptions=(ConnectionError, TimeoutError)
)


# =============================================================================
# RETRY DECORATOR
# =============================================================================

def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator to add retry logic with exponential backoff to any function.
    
    Args:
        config: RetryConfig instance. If None, uses API_RETRY_CONFIG
        
    Usage:
        @with_retry()
        def my_function():
            # Your code here
            pass
            
        @with_retry(FILE_RETRY_CONFIG)
        def save_file():
            # File operations
            pass
    """
    if config is None:
        config = API_RETRY_CONFIG
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            last_exception = None
            
            for attempt in range(config.max_attempts):
                # Check if we've exceeded total timeout
                if config.timeout and (time.time() - start_time) > config.timeout:
                    error_msg = (
                        f"Operation '{func.__name__}' exceeded timeout of "
                        f"{config.timeout}s after {attempt} attempts"
                    )
                    logger.error(error_msg)
                    raise TimeoutError(error_msg)
                
                try:
                    # Attempt the operation
                    result = func(*args, **kwargs)
                    
                    # Success - log if this wasn't the first attempt
                    if attempt > 0:
                        logger.info(
                            f"Operation '{func.__name__}' succeeded on attempt {attempt + 1}"
                        )
                    
                    return result
                    
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    # Log the failure
                    logger.warning(
                        f"Operation '{func.__name__}' failed on attempt {attempt + 1}/{config.max_attempts}: "
                        f"{type(e).__name__}: {str(e)}"
                    )
                    
                    # If this was the last attempt, don't sleep
                    if attempt == config.max_attempts - 1:
                        break
                    
                    # Calculate delay and sleep
                    delay = config.calculate_delay(attempt)
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                
                except Exception as e:
                    # Non-retryable exception - fail immediately
                    logger.error(
                        f"Operation '{func.__name__}' failed with non-retryable error: "
                        f"{type(e).__name__}: {str(e)}"
                    )
                    raise
            
            # All attempts exhausted
            error_msg = (
                f"Operation '{func.__name__}' failed after {config.max_attempts} attempts. "
                f"Last error: {type(last_exception).__name__}: {str(last_exception)}"
            )
            logger.error(error_msg)
            
            # Raise a more informative exception
            raise RetryExhaustedError(error_msg) from last_exception
        
        return wrapper
    return decorator


# =============================================================================
# ASYNC RETRY DECORATOR
# =============================================================================

def with_async_retry(config: Optional[RetryConfig] = None):
    """
    Async version of retry decorator for async functions.
    
    Usage:
        @with_async_retry()
        async def my_async_function():
            # Your async code here
            pass
    """
    if config is None:
        config = API_RETRY_CONFIG
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            import asyncio
            
            start_time = time.time()
            last_exception = None
            
            for attempt in range(config.max_attempts):
                # Check timeout
                if config.timeout and (time.time() - start_time) > config.timeout:
                    error_msg = (
                        f"Async operation '{func.__name__}' exceeded timeout of "
                        f"{config.timeout}s after {attempt} attempts"
                    )
                    logger.error(error_msg)
                    raise TimeoutError(error_msg)
                
                try:
                    result = await func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(
                            f"Async operation '{func.__name__}' succeeded on attempt {attempt + 1}"
                        )
                    
                    return result
                    
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    logger.warning(
                        f"Async operation '{func.__name__}' failed on attempt {attempt + 1}/{config.max_attempts}: "
                        f"{type(e).__name__}: {str(e)}"
                    )
                    
                    if attempt == config.max_attempts - 1:
                        break
                    
                    delay = config.calculate_delay(attempt)
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
                
                except Exception as e:
                    logger.error(
                        f"Async operation '{func.__name__}' failed with non-retryable error: "
                        f"{type(e).__name__}: {str(e)}"
                    )
                    raise
            
            error_msg = (
                f"Async operation '{func.__name__}' failed after {config.max_attempts} attempts. "
                f"Last error: {type(last_exception).__name__}: {str(last_exception)}"
            )
            logger.error(error_msg)
            raise RetryExhaustedError(error_msg) from last_exception
        
        return wrapper
    return decorator


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""
    pass


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_custom_config(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    **kwargs
) -> RetryConfig:
    """
    Create a custom retry configuration.
    
    Args:
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay in seconds
        **kwargs: Additional RetryConfig parameters
        
    Returns:
        RetryConfig instance
    """
    return RetryConfig(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        **kwargs
    )


def get_user_friendly_error(exception: Exception) -> str:
    """
    Convert technical exception into user-friendly error message.
    
    Args:
        exception: The exception to convert
        
    Returns:
        User-friendly error message
    """
    error_messages = {
        ConnectionError: "Unable to connect to the service. Please check your internet connection.",
        TimeoutError: "The request took too long to complete. Please try again.",
        RetryExhaustedError: "The operation failed after multiple attempts. Please try again later.",
        PermissionError: "Permission denied. Please check file permissions.",
        IOError: "An error occurred while accessing the file.",
        OSError: "A system error occurred. Please try again.",
    }
    
    exception_type = type(exception)
    
    # Check for specific exception types
    for exc_type, message in error_messages.items():
        if isinstance(exception, exc_type):
            return message
    
    # Generic fallback
    return f"An unexpected error occurred: {str(exception)}"


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

if __name__ == "__main__":
    # Example 1: Basic retry
    @with_retry()
    def unreliable_api_call():
        import random
        if random.random() < 0.7:  # 70% failure rate
            raise ConnectionError("API temporarily unavailable")
        return "Success!"
    
    # Example 2: Custom configuration
    custom_config = RetryConfig(
        max_attempts=2,
        initial_delay=0.5,
        max_delay=10.0
    )
    
    @with_retry(custom_config)
    def custom_operation():
        print("Attempting operation...")
        raise Exception("Simulated failure")
    
    # Example 3: File operations
    @with_retry(FILE_RETRY_CONFIG)
    def save_important_file():
        with open("test.txt", "w") as f:
            f.write("Important data")
        return "File saved"
    
    # Test the examples
    try:
        result = unreliable_api_call()
        print(f"Result: {result}")
    except RetryExhaustedError as e:
        print(f"Failed: {get_user_friendly_error(e)}")
