#!/usr/bin/env python
"""
Test script for verifying the duration formatting in the Reddit Sentiment Analysis GUI.

This script simulates different durations and tests the format_duration function
to ensure it correctly formats time periods in a user-friendly way.
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to the Python path to ensure imports work
project_root = Path(__file__).parent.absolute()
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("duration_format_test")


def main():
    """Test the duration formatting functionality."""
    print("=" * 80)
    print("Testing Duration Formatting for Reddit Sentiment Analysis".center(80))
    print("=" * 80)

    # Import the format_duration function
    try:
        from app.src.reddit_sentiment_analysis.gui import format_duration

        logger.info("Successfully imported format_duration function")
    except ImportError as e:
        logger.error(f"Failed to import format_duration function: {e}")
        print(
            "ERROR: Could not import the format_duration function. Make sure you're running this from the project root."
        )
        return

    # Test cases with expected outputs
    test_cases = [
        (timedelta(seconds=30), "Just started"),
        (timedelta(minutes=1), "1 minute"),
        (timedelta(minutes=5), "5 minutes"),
        (timedelta(hours=1), "1 hour"),
        (timedelta(hours=1, minutes=30), "1 hour, 30 minutes"),
        (timedelta(hours=2), "2 hours"),
        (timedelta(days=1), "1 day"),
        (timedelta(days=1, hours=6), "1 day, 6 hours"),
        (timedelta(days=1, minutes=45), "1 day, 45 minutes"),
        (timedelta(days=2, hours=5, minutes=30), "2 days, 5 hours"),
        (timedelta(days=7), "7 days"),
        (timedelta(days=30), "30 days"),
    ]

    # Run the tests
    passed = 0
    failed = 0

    print("\nRunning test cases...\n")
    for duration, expected in test_cases:
        result = format_duration(duration)
        if result == expected:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"
            failed += 1

        print(
            f"{status}: Duration: {duration} → Expected: '{expected}' → Got: '{result}'"
        )

    # Print summary
    print("\n" + "-" * 80)
    print(f"Test Summary: {passed} passed, {failed} failed")

    # Test actual duration from a specific start time
    print("\nTesting with real timestamps:")

    # Test a start time from 1 hour ago
    one_hour_ago = datetime.now() - timedelta(hours=1, minutes=15)
    duration = datetime.now() - one_hour_ago
    formatted = format_duration(duration)
    print(f"Start time 1 hour and 15 minutes ago: {formatted}")

    # Test a start time from yesterday
    yesterday = datetime.now() - timedelta(days=1, hours=2)
    duration = datetime.now() - yesterday
    formatted = format_duration(duration)
    print(f"Start time from yesterday: {formatted}")

    # Test a longer duration
    week_ago = datetime.now() - timedelta(days=7, hours=5)
    duration = datetime.now() - week_ago
    formatted = format_duration(duration)
    print(f"Start time from a week ago: {formatted}")

    print("\n" + "=" * 80)
    print("Test complete!".center(80))
    print("=" * 80)


if __name__ == "__main__":
    main()
