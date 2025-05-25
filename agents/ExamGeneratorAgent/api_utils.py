import time
import logging
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

# Type variable for the return type of the function
T = TypeVar('T')

def retry_api_call(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions_to_retry: tuple = (Exception,)
) -> T:
    """
    Retry an API call with exponential backoff.
    
    Args:
        func: The function to call
        max_retries: The maximum number of retries
        initial_delay: The initial delay in seconds
        backoff_factor: The factor to multiply the delay by after each retry
        exceptions_to_retry: The exceptions to retry on
        
    Returns:
        The result of the function call
    """
    retries = 0
    delay = initial_delay
    
    while True:
        try:
            return func()
        except exceptions_to_retry as e:
            retries += 1
            if retries > max_retries:
                logger.error(f"Maximum retries ({max_retries}) exceeded: {str(e)}")
                raise
            
            logger.warning(f"API call failed (attempt {retries}/{max_retries}): {str(e)}")
            logger.info(f"Retrying in {delay:.2f} seconds...")
            
            time.sleep(delay)
            delay *= backoff_factor
