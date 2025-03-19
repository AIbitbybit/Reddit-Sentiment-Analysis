"""
Rate limiting utilities for API interactions.
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Global dict to store last API call times per endpoint
_last_api_call_times: Dict[str, float] = {}


def throttle(min_interval: float = 1.0, key: Optional[str] = None):
    """
    Decorator to throttle API calls to avoid rate limiting.

    Args:
        min_interval: Minimum time in seconds between API calls
        key: Optional key to use for tracking different endpoints

    Returns:
        Decorated function
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Use function name as key if not provided
            throttle_key = key or func.__name__

            # Check when the last call was made
            last_call_time = _last_api_call_times.get(throttle_key, 0)
            current_time = time.time()
            elapsed = current_time - last_call_time

            # If we need to wait, do so
            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                logger.debug(
                    f"Throttling: waiting {wait_time:.2f}s before calling {throttle_key}"
                )
                time.sleep(wait_time)

            # Update the last call time
            _last_api_call_times[throttle_key] = time.time()

            # Call the function
            return func(*args, **kwargs)

        return wrapper

    return decorator


def with_retry(
    max_retries: int = 3, base_delay: float = 2.0, backoff_factor: float = 2.0
):
    """
    Decorator to retry API calls with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        backoff_factor: Factor to increase delay by on each retry

    Returns:
        Decorated function
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            last_exception = None

            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    retries += 1

                    # Check if we've exhausted retries
                    if retries > max_retries:
                        break

                    # Calculate delay with exponential backoff
                    delay = base_delay * (backoff_factor ** (retries - 1))

                    # Check if it's a rate limit error
                    is_rate_limit = False
                    if hasattr(e, "response") and hasattr(e.response, "status_code"):
                        is_rate_limit = e.response.status_code == 429
                    elif "429" in str(e) or "rate limit" in str(e).lower():
                        is_rate_limit = True

                    if is_rate_limit:
                        logger.warning(
                            f"Rate limit hit. Retrying in {delay:.2f}s... (Attempt {retries}/{max_retries})"
                        )
                    else:
                        logger.warning(
                            f"Error: {str(e)}. Retrying in {delay:.2f}s... (Attempt {retries}/{max_retries})"
                        )

                    time.sleep(delay)

            # If we get here, all retries failed
            logger.error(
                f"All {max_retries} retry attempts failed. Last error: {str(last_exception)}"
            )
            raise last_exception

        return wrapper

    return decorator
