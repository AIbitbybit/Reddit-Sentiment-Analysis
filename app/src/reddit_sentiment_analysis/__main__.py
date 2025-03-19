"""
Main entry point for the Reddit sentiment analysis application.
"""

import asyncio
import logging
import os
import time
from typing import List, Optional

from .config import DEFAULT_KEY_TERMS, DEFAULT_SUBREDDITS, REFRESH_INTERVAL_MINUTES
from .monitoring import RedditMonitor
from .utils import check_internet_connectivity

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def monitor_reddit(
    key_term: str,
    email: str,
    subreddits: Optional[List[str]] = None,
    refresh_interval: int = REFRESH_INTERVAL_MINUTES,
):
    """
    Monitor Reddit for new comments containing the key term.

    Args:
        key_term: Term to search for
        email: Email address for notifications
        subreddits: List of subreddits to monitor
        refresh_interval: How often to check for new comments (in minutes)
    """
    monitor = RedditMonitor(key_term, email, subreddits)

    logger.info(
        f"Starting Reddit monitor for term '{key_term}' (checking every {refresh_interval} minutes)"
    )

    while True:
        try:
            # Check for OpenAI API connectivity
            connectivity, error = check_internet_connectivity(host="api.openai.com")
            if not connectivity:
                logger.error(f"Cannot connect to OpenAI API: {error}")
                logger.info(f"Will retry in {refresh_interval} minutes...")
                time.sleep(refresh_interval * 60)
                continue

            # Check for new comments
            comments = await monitor.check_for_new_comments()
            logger.info(f"Found {len(comments)} new comments matching '{key_term}'")

            refresh_delay = refresh_interval * 60
            logger.info(f"Waiting {refresh_interval} minutes until next scan")
            time.sleep(refresh_delay)
        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")
            break
        except Exception as e:
            logger.error(f"Error during monitoring: {str(e)}")
            logger.info(f"Retrying in 60 seconds...")
            time.sleep(60)


if __name__ == "__main__":
    key_term = os.getenv("REDDIT_KEY_TERM") or DEFAULT_KEY_TERMS[0]
    email = os.getenv("NOTIFICATION_EMAIL", "")

    # Run the monitor
    asyncio.run(monitor_reddit(key_term, email))
