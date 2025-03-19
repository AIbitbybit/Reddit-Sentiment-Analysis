"""
Data collector for fetching and saving Reddit data.
"""

import asyncio
import concurrent.futures
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..config import DEFAULT_POST_LIMIT, DEFAULT_SUBREDDITS, DEFAULT_TIME_FILTER
from .reddit_client import RedditClient

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataCollector:
    """Collector for fetching and saving Reddit data."""

    def __init__(
        self,
        output_dir: Union[str, Path] = "data/raw",
        reddit_client: Optional[RedditClient] = None,
    ):
        """
        Initialize the data collector.

        Args:
            output_dir: Directory to save collected data
            reddit_client: Reddit client instance
        """
        self.output_dir = Path(output_dir)
        self.reddit_client = reddit_client or RedditClient()

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(
            f"Data collector initialized with output directory: {self.output_dir}"
        )

    def collect_data(
        self,
        subreddits: List[str] = None,
        time_filter: str = DEFAULT_TIME_FILTER,
        limit: int = DEFAULT_POST_LIMIT,
        filter_business: bool = True,
        save: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Collect data from Reddit.

        Args:
            subreddits: List of subreddit names to fetch posts from
            time_filter: Time filter for posts
            limit: Maximum number of posts to fetch per subreddit
            filter_business: Whether to filter posts for business-related content
            save: Whether to save the collected data

        Returns:
            List of post dictionaries
        """
        subreddits = subreddits or DEFAULT_SUBREDDITS
        logger.info(f"Collecting data from subreddits: {', '.join(subreddits)}")

        # Fetch posts from Reddit
        posts = self.reddit_client.fetch_posts(
            subreddits=subreddits,
            time_filter=time_filter,
            limit=limit,
            filter_business=filter_business,
        )

        if save and posts:
            self._save_data(posts)

        return posts

    def collect_by_search(
        self,
        query: str,
        subreddits: List[str] = None,
        time_filter: str = DEFAULT_TIME_FILTER,
        limit: int = DEFAULT_POST_LIMIT,
        save: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Collect data from Reddit by search query.

        Args:
            query: Search query
            subreddits: List of subreddit names to search in
            time_filter: Time filter for posts
            limit: Maximum number of posts to fetch
            save: Whether to save the collected data

        Returns:
            List of post dictionaries
        """
        subreddits = subreddits or DEFAULT_SUBREDDITS
        logger.info(f"Searching for '{query}' in subreddits: {', '.join(subreddits)}")

        # Search for posts on Reddit
        posts = self.reddit_client.search_posts(
            query=query, subreddits=subreddits, time_filter=time_filter, limit=limit
        )

        if save and posts:
            self._save_data(posts, filename_prefix=f"search_{query.replace(' ', '_')}")

        return posts

    def _save_data(
        self, data: List[Dict[str, Any]], filename_prefix: str = "reddit_data"
    ) -> None:
        """
        Save data to a JSON file.

        Args:
            data: Data to save
            filename_prefix: Prefix for the output filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.json"
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(data)} posts to {filepath}")

    def load_data(self, filepath: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Load data from a JSON file.

        Args:
            filepath: Path to the JSON file

        Returns:
            List of post dictionaries
        """
        filepath = Path(filepath)

        if not filepath.exists():
            logger.error(f"File not found: {filepath}")
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"Loaded {len(data)} posts from {filepath}")
        return data

    async def get_new_comments(
        self, key_term: str, subreddits: List[str], time_limit: int = 86400
    ) -> List[Dict[str, Any]]:
        """
        Get new comments containing a specific key term from specified subreddits.

        Args:
            key_term: Term to search for in comments
            subreddits: List of subreddits to search
            time_limit: Time limit in seconds to look back (default: 24 hours)

        Returns:
            List of comment dictionaries containing the key term
        """
        logger.info(
            f"Searching for comments containing '{key_term}' in: {', '.join(subreddits)}"
        )
        logger.info(
            f"Looking back {time_limit} seconds (approx. {time_limit/3600:.1f} hours)"
        )

        # Get current time minus time_limit
        since_time = datetime.now().timestamp() - time_limit
        since_date = datetime.fromtimestamp(since_time).strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Looking for comments since: {since_date}")

        all_matching_comments = []

        # Create a function to run PRAW operations in a synchronous context
        def get_subreddit_comments(subreddit_name, since_time_val, limit_val):
            try:
                logger.info(
                    f"Fetching up to {limit_val} comments from r/{subreddit_name}"
                )

                # Get recent comments from this subreddit
                # The RedditClient now handles rate limiting internally
                comments = self.reddit_client.get_recent_comments(
                    subreddit=subreddit_name, since_time=since_time_val, limit=limit_val
                )
                logger.info(
                    f"Retrieved {len(comments)} comments from r/{subreddit_name}"
                )
                return comments
            except Exception as e:
                logger.error(
                    f"Error fetching comments from r/{subreddit_name}: {str(e)}"
                )
                return []

        # Process each subreddit
        for subreddit in subreddits:
            logger.info(f"Processing subreddit: r/{subreddit}")
            # Run PRAW operations in a way that avoids async warnings
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # This runs the PRAW operations in a separate thread, which is better for sync operations
                # Increase comment limit to 50 to capture more recent comments
                recent_comments = await asyncio.get_event_loop().run_in_executor(
                    executor, get_subreddit_comments, subreddit, since_time, 50
                )

                # Add a short delay between subreddit requests to avoid rate limiting
                await asyncio.sleep(2)

            # Filter comments containing the key term (case insensitive)
            key_term_lower = key_term.lower()
            matching_comments = [
                comment
                for comment in recent_comments
                if key_term_lower in comment["body"].lower()
            ]

            logger.info(
                f"Found {len(matching_comments)} comments containing '{key_term}' in r/{subreddit}"
            )
            all_matching_comments.extend(matching_comments)

        # Sort comments by creation time (newest first)
        all_matching_comments.sort(key=lambda x: x["created_utc"], reverse=True)

        logger.info(
            f"Total comments found containing '{key_term}': {len(all_matching_comments)}"
        )

        # Log the first few comments for debugging
        if all_matching_comments:
            logger.info("Sample of matching comments:")
            for i, comment in enumerate(all_matching_comments[:3]):
                created_time = datetime.fromtimestamp(comment["created_utc"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                logger.info(
                    f"Comment {i+1}: ID={comment['id']}, Author={comment['author']}, Created={created_time}"
                )
                logger.info(f"Text: {comment['body'][:100]}...")

            # Log the most recent comment in detail
            if all_matching_comments:
                most_recent = all_matching_comments[0]
                logger.info(f"Most recent comment details:")
                for key, value in most_recent.items():
                    if key != "body":  # Don't log the full body twice
                        logger.info(f"  {key}: {value}")
                logger.info(f"  body (first 200 chars): {most_recent['body'][:200]}")

        return all_matching_comments

    async def post_response(self, comment_id: str, response_text: str) -> bool:
        """
        Post a response to a Reddit comment.

        Args:
            comment_id: ID of the comment to respond to
            response_text: Text of the response

        Returns:
            True if posted successfully, False otherwise
        """
        logger.info(f"Posting response to comment {comment_id}")

        try:
            # Create a function to run PRAW operations in a synchronous context
            def post_reddit_comment(cid, text):
                # Post the response using the Reddit client
                return self.reddit_client.reply_to_comment(cid, text)

            # Run PRAW operations in a way that avoids async warnings
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # This runs the PRAW operations in a separate thread
                result = await asyncio.get_event_loop().run_in_executor(
                    executor, post_reddit_comment, comment_id, response_text
                )

            if result:
                logger.info(f"Successfully posted response to comment {comment_id}")
            else:
                logger.error(f"Failed to post response to comment {comment_id}")

            return result

        except Exception as e:
            logger.error(f"Error posting response to comment {comment_id}: {str(e)}")
            return False
