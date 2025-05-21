import time
import logging
import json
from typing import Any, Callable, Dict, Optional, TypeVar

# Set up logging
logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_api_call(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    **kwargs: Any,
) -> T:
    """
    Execute an API call with retry logic.

    Args:
        func: The function to call
        *args: Positional arguments to pass to the function
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds before retrying
        backoff_factor: Factor by which the delay increases with each retry
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function call

    Raises:
        Exception: The last exception encountered if all retries fail
    """
    last_exception = None
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            logger.warning(
                f"API call failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
            )

            # If we've exhausted our retries, raise the last exception
            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} attempts failed: {str(e)}")
                raise

            # Wait before retrying, with exponential backoff
            logger.info(f"Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= backoff_factor

    # This should never happen, but just in case
    if last_exception:
        raise last_exception
    raise Exception("All retries failed without a specific exception")


def safe_json_parse(
    json_str: str, default_value: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Safely parse a JSON string.

    Args:
        json_str: JSON string to parse
        default_value: Default value to return if parsing fails

    Returns:
        Parsed JSON object or default value
    """
    if not json_str or not json_str.strip():
        logger.warning("Empty JSON string received")
        return default_value or {}

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {str(e)}, content: {json_str[:100]}...")
        return default_value or {}
