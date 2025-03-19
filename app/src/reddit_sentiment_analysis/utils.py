"""
Utility functions for the Reddit sentiment analysis application.
"""

import logging
import socket
import time
from typing import Optional, Tuple

logger = logging.getLogger("reddit_sentiment_analysis.utils")


def check_internet_connectivity(
    host: str = "api.openai.com", port: int = 443, timeout: int = 5
) -> Tuple[bool, Optional[str]]:
    """
    Check if there is a working internet connection to the specified host.

    Args:
        host: The host to check connectivity to
        port: The port to connect on
        timeout: The timeout in seconds

    Returns:
        Tuple of (is_connected, error_message)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True, None
    except socket.error as e:
        error_message = f"Connection error to {host}:{port}: {str(e)}"
        logger.warning(error_message)
        return False, error_message


def backoff_retry(func, max_retries: int = 3, base_delay: float = 1.0):
    """
    Retry a function with exponential backoff.

    Args:
        func: The function to retry
        max_retries: Maximum number of retries
        base_delay: Base delay in seconds between retries

    Returns:
        The result of the function call, or raises the last exception
    """
    last_exception = None

    for retry in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            delay = base_delay * (2**retry)
            logger.warning(
                f"Function failed, retrying in {delay:.1f} seconds... ({retry+1}/{max_retries})"
            )
            logger.warning(f"Error: {str(e)}")
            time.sleep(delay)

    if last_exception:
        raise last_exception
