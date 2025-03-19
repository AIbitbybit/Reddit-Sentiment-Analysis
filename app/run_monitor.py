#!/usr/bin/env python3
"""
Command-line launcher for Reddit Sentiment Analysis monitoring.
This script launches the command-line monitor with simplified arguments.
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure we can import the app module
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def main():
    """Parse arguments and launch the monitor."""
    parser = argparse.ArgumentParser(description="Reddit Sentiment Analysis Monitor")
    parser.add_argument("key_term", help="Term to monitor (e.g., your company name)")
    parser.add_argument("email", help="Email to receive alerts")
    parser.add_argument(
        "--subreddits",
        "-s",
        help="Comma-separated list of subreddits (default: business,smallbusiness)",
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=300,
        help="Check interval in seconds (default: 300)",
    )

    args = parser.parse_args()

    # Import here to avoid import errors before path setup
    from src.reddit_sentiment_analysis.command_monitor import run_command_monitor

    # Pass args to the command_monitor module
    sys.argv = [sys.argv[0]]
    sys.argv.extend(["--key-term", args.key_term])
    sys.argv.extend(["--email", args.email])

    if args.subreddits:
        sys.argv.extend(["--subreddits", args.subreddits])

    sys.argv.extend(["--interval", str(args.interval)])

    return run_command_monitor()


if __name__ == "__main__":
    sys.exit(main())
