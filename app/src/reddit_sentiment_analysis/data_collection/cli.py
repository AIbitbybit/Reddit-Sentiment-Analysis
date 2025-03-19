"""
Command-line interface for the data collection module.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from ..config import DEFAULT_POST_LIMIT, DEFAULT_SUBREDDITS, DEFAULT_TIME_FILTER
from .collector import DataCollector

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Collect data from Reddit for sentiment analysis."
    )

    # Subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Parser for the 'collect' command
    collect_parser = subparsers.add_parser(
        "collect", help="Collect posts from subreddits"
    )
    collect_parser.add_argument(
        "--subreddits",
        "-s",
        nargs="+",
        default=DEFAULT_SUBREDDITS,
        help=f"Subreddits to collect posts from (default: {', '.join(DEFAULT_SUBREDDITS)})",
    )
    collect_parser.add_argument(
        "--time-filter",
        "-t",
        choices=["hour", "day", "week", "month", "year", "all"],
        default=DEFAULT_TIME_FILTER,
        help=f"Time filter for posts (default: {DEFAULT_TIME_FILTER})",
    )
    collect_parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=DEFAULT_POST_LIMIT,
        help=f"Maximum number of posts to fetch per subreddit (default: {DEFAULT_POST_LIMIT})",
    )
    collect_parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="data/raw",
        help="Directory to save collected data (default: data/raw)",
    )
    collect_parser.add_argument(
        "--no-filter",
        action="store_true",
        help="Disable filtering for business-related content",
    )

    # Parser for the 'search' command
    search_parser = subparsers.add_parser(
        "search", help="Search for posts matching a query"
    )
    search_parser.add_argument("query", type=str, help="Search query")
    search_parser.add_argument(
        "--subreddits",
        "-s",
        nargs="+",
        default=DEFAULT_SUBREDDITS,
        help=f"Subreddits to search in (default: {', '.join(DEFAULT_SUBREDDITS)})",
    )
    search_parser.add_argument(
        "--time-filter",
        "-t",
        choices=["hour", "day", "week", "month", "year", "all"],
        default=DEFAULT_TIME_FILTER,
        help=f"Time filter for posts (default: {DEFAULT_TIME_FILTER})",
    )
    search_parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=DEFAULT_POST_LIMIT,
        help=f"Maximum number of posts to fetch (default: {DEFAULT_POST_LIMIT})",
    )
    search_parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="data/raw",
        help="Directory to save collected data (default: data/raw)",
    )

    return parser.parse_args()


def main():
    """Main entry point for the data collection CLI."""
    args = parse_args()

    if not args.command:
        logger.error("No command specified. Use 'collect' or 'search'.")
        sys.exit(1)

    # Create data collector
    collector = DataCollector(output_dir=args.output_dir)

    if args.command == "collect":
        # Collect posts from subreddits
        posts = collector.collect_data(
            subreddits=args.subreddits,
            time_filter=args.time_filter,
            limit=args.limit,
            filter_business=not args.no_filter,
        )
        logger.info(
            f"Collected {len(posts)} posts from {len(args.subreddits)} subreddits"
        )

    elif args.command == "search":
        # Search for posts matching a query
        posts = collector.collect_by_search(
            query=args.query,
            subreddits=args.subreddits,
            time_filter=args.time_filter,
            limit=args.limit,
        )
        logger.info(f"Found {len(posts)} posts matching query '{args.query}'")

    else:
        logger.error(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
