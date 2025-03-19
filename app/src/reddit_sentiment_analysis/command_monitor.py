#!/usr/bin/env python3
"""
Command-line monitoring script for Reddit Sentiment Analysis.
This script runs in a synchronous context to avoid PRAW async warnings.
"""

import argparse
import logging
import os
import signal
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from .config import DEFAULT_SUBREDDITS
from .data_collection.collector import DataCollector
from .email_service import EmailService
from .monitoring import RedditMonitor
from .storage.comment_db import CommentDatabase

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global monitoring flag
stop_monitoring = False


def signal_handler(sig, frame):
    """Handle interrupt signals."""
    global stop_monitoring
    logger.info("Stopping monitoring (signal received)...")
    stop_monitoring = True


def check_api_key():
    """Check if OpenAI API key is valid and prompt for a new one if needed."""
    api_key = os.getenv("OPENAI_API_KEY")

    # Check if API key is missing or using placeholder text
    if not api_key or api_key in [
        "your_openai_api_key_here",
        "sk-your-actual-openai-api-key",
        "${OPENAI_API_KEY}",
    ]:
        print("\033[93mOpenAI API key is missing or invalid.\033[0m")
        print("You need a valid OpenAI API key to analyze sentiment.")
        print("Get your API key from: https://platform.openai.com/account/api-keys")

        new_key = input("\n\033[92mEnter your OpenAI API key: \033[0m")

        if new_key and new_key.strip():
            # Update environment variable in memory
            os.environ["OPENAI_API_KEY"] = new_key.strip()

            # Get the path to the .env file
            env_path = Path(".") / ".env"
            if not env_path.exists():
                env_path = Path("..") / ".env"
            if not env_path.exists():
                env_path = Path("../..") / ".env"

            if env_path.exists():
                # Update the .env file
                with open(env_path, "r") as f:
                    lines = f.readlines()

                with open(env_path, "w") as f:
                    for line in lines:
                        if line.startswith("OPENAI_API_KEY="):
                            f.write(f"OPENAI_API_KEY={new_key.strip()}\n")
                        else:
                            f.write(line)

                print("\033[92mAPI key updated successfully!\033[0m")
            else:
                print("\033[93mCould not find .env file to save API key.\033[0m")
                print("The key will be used for this session only.")

            return True
        else:
            print("\033[91mNo API key provided. Sentiment analysis may fail.\033[0m")
            return False

    return True


def main_loop(monitor, check_interval=300):
    """
    Main monitoring loop.

    Args:
        monitor: The RedditMonitor instance
        check_interval: Seconds between checks (default: 5 minutes)
    """
    global stop_monitoring
    stop_monitoring = False

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting monitoring loop...")
    logger.info(f"Checking for new comments every {check_interval} seconds")

    while not stop_monitoring:
        try:
            logger.info("Checking for new comments...")
            # Use the event loop just for this call
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            comments = loop.run_until_complete(monitor.check_for_new_comments())
            loop.close()

            if comments:
                logger.info(f"Processed {len(comments)} new comments")
            else:
                logger.info("No new comments found")

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")

        # Use shorter sleep intervals to be more responsive to stop signals
        for _ in range(check_interval):
            if stop_monitoring:
                break
            time.sleep(1)

    logger.info("Monitoring stopped")


def run_command_monitor():
    """Run the command-line monitor."""
    parser = argparse.ArgumentParser(description="Reddit Sentiment Monitor")
    parser.add_argument(
        "--key-term",
        "-k",
        type=str,
        required=True,
        help="Key term to search for (e.g., your company name)",
    )
    parser.add_argument(
        "--email", "-e", type=str, required=True, help="Email address for notifications"
    )
    parser.add_argument(
        "--subreddits",
        "-s",
        type=str,
        default=",".join(DEFAULT_SUBREDDITS),
        help=f"Comma-separated list of subreddits to monitor (default: {','.join(DEFAULT_SUBREDDITS)})",
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=300,
        help="Check interval in seconds (default: 300)",
    )

    args = parser.parse_args()

    # Split subreddits
    subreddits = [s.strip() for s in args.subreddits.split(",")]

    # Check OpenAI API key
    if not check_api_key():
        return 1

    print("\n\033[96m====== Reddit Sentiment Analysis ======\033[0m")
    print("\033[96mCommand-Line Monitoring Mode\033[0m")
    print(
        f"\nMonitoring comments containing '\033[1m{args.key_term}\033[0m' in: {', '.join(subreddits)}"
    )
    print(f"Alerts will be sent to: \033[1m{args.email}\033[0m")
    print("\nPress Ctrl+C to stop monitoring")

    # Initialize the database
    db = CommentDatabase()

    # Create a monitor
    monitor = RedditMonitor(
        key_term=args.key_term, email=args.email, subreddits=subreddits, db=db
    )

    # Run the main loop
    main_loop(monitor, args.interval)

    return 0


if __name__ == "__main__":
    sys.exit(run_command_monitor())
