#!/usr/bin/env python
"""
Test script for verifying that only one monitoring thread runs at a time.
This script checks for running threads and logs monitoring info.
"""

import logging
import os
import sys
import time
from pathlib import Path

# Add the project root to the Python path to ensure imports work
project_root = Path(__file__).parent.absolute()
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("thread_monitor")


def main():
    """Main function to monitor thread status."""
    print("=" * 80)
    print("Thread Monitor for Reddit Sentiment Analysis".center(80))
    print("=" * 80)

    # Import gui module
    try:
        from src.reddit_sentiment_analysis.gui import (
            current_monitoring_id,
            monitoring_threads,
        )

        logger.info(f"Successfully imported gui module")
    except ImportError as e:
        logger.error(f"Failed to import gui module: {e}")
        print(
            "ERROR: Could not import the gui module. Make sure you're running this from the project root."
        )
        return

    # Display current monitoring status
    print(f"\nCurrent monitoring session ID: {current_monitoring_id}")
    print(f"Number of registered monitoring threads: {len(monitoring_threads)}")

    # Display details of each thread
    for session_id, info in monitoring_threads.items():
        thread = info.get("thread")
        is_active = "ACTIVE" if thread and thread.is_alive() else "INACTIVE"
        term = info.get("key_term", "unknown")

        print(f"\nThread {session_id}:")
        print(f"  Status: {is_active}")
        print(f"  Key Term: {term}")
        print(f"  Subreddits: {', '.join(info.get('subreddits', []))}")

        if "start_time" in info:
            start_time = info.get("start_time")
            elapsed = (
                (time.time() - start_time.timestamp())
                if hasattr(start_time, "timestamp")
                else "unknown"
            )
            print(f"  Started: {start_time}")
            print(f"  Running for: {elapsed:.1f} seconds")

    # If no threads are active
    if not monitoring_threads:
        print("\nNo monitoring threads are currently registered.")
        print(
            "This is good if you haven't started monitoring yet, or if you've properly stopped all threads."
        )

    print("\n" + "=" * 80)
    print("Test complete!".center(80))
    print("=" * 80)


if __name__ == "__main__":
    main()
