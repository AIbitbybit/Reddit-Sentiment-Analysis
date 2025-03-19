"""
Utility functions for the Reddit Sentiment Analysis application.
"""

import logging
import socket
from typing import Tuple

from .rate_limiting import throttle, with_retry

# Set up logging
logger = logging.getLogger(__name__)


def check_internet_connectivity(
    host: str = "api.openai.com", port: int = 443, timeout: float = 5.0
) -> Tuple[bool, str]:
    """
    Check if the internet is available by attempting to connect to a specific host.

    Args:
        host: The host to connect to (default: api.openai.com)
        port: The port to connect to (default: 443 for HTTPS)
        timeout: The timeout in seconds for the connection attempt

    Returns:
        A tuple of (is_connected, error_message)
    """
    try:
        # Try to establish a connection to the host
        socket.create_connection((host, port), timeout=timeout)
        logger.info(f"Internet connection check successful: connected to {host}:{port}")
        return True, ""
    except OSError as e:
        error_message = f"Failed to connect to {host}:{port} - {str(e)}"
        logger.warning(f"Internet connection check failed: {error_message}")
        return False, error_message


__all__ = ["check_internet_connectivity", "throttle", "with_retry"]
