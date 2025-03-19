#!/usr/bin/env python
"""
Test script for Reddit OAuth authentication flow.
This script tests the full flow of authenticating with Reddit via OAuth,
fetching comments, and optionally testing comment posting functionality.
"""

import argparse
import logging
import os
import sys
import traceback
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_reddit_oauth")

# Import from the package
from src.reddit_sentiment_analysis.data_collection.reddit_client import (
    TOKEN_PATH,
    RedditClient,
)


def test_oauth_flow(
    force_auth=False,
    test_posting=False,
    subreddit="AskReddit",
    verbose=False,
    manual_auth=False,
):
    """
    Test the OAuth authentication flow.

    Args:
        force_auth: If True, force re-authentication even if already authenticated
        test_posting: If True, test posting a comment (requires authentication)
        subreddit: The subreddit to fetch comments from
        verbose: If True, enable more verbose logging
        manual_auth: If True, use the manual authentication flow instead of the automatic one
    """
    if verbose:
        # Set logging level to DEBUG for more detailed output
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("src.reddit_sentiment_analysis").setLevel(logging.DEBUG)

    logger.info("Testing Reddit OAuth authentication...")

    # Print configuration for debugging
    logger.info(f"Current configuration:")
    logger.info(
        f"  Client ID: {'*' * 5}{os.getenv('REDDIT_CLIENT_ID')[-4:] if os.getenv('REDDIT_CLIENT_ID') else 'Not set'}"
    )
    logger.info(
        f"  Client Secret: {'*' * 5}{os.getenv('REDDIT_CLIENT_SECRET')[-4:] if os.getenv('REDDIT_CLIENT_SECRET') else 'Not set'}"
    )
    logger.info(f"  Redirect URI: {os.getenv('REDDIT_REDIRECT_URI', 'Not set')}")
    logger.info(f"  Token Path: {TOKEN_PATH} (exists: {TOKEN_PATH.exists()})")

    # Initialize the Reddit client
    logger.info("Initializing Reddit client...")
    client = RedditClient()

    # Delete token if force auth is enabled
    if force_auth and TOKEN_PATH.exists():
        logger.info(f"Force auth enabled, deleting existing token at {TOKEN_PATH}")
        TOKEN_PATH.unlink()

    # Check authentication status
    if client.is_authenticated and client.can_post:
        logger.info(f"Already authenticated as u/{client.username}")
    else:
        logger.info("Not authenticated. Starting OAuth flow...")

        # Choose authentication method
        if manual_auth:
            logger.info("Using manual authentication flow...")
            success = client.authenticate_manual()
        else:
            logger.info("Using automatic authentication flow...")
            success = client.authenticate()

        if success:
            logger.info(
                f"Authentication successful! Authenticated as u/{client.username}"
            )
        else:
            logger.error("Authentication failed!")
            return False

    # Test fetching comments
    try:
        logger.info(f"Fetching recent comments from r/{subreddit}...")
        comments = client.get_recent_comments(subreddit=subreddit, limit=1)

        if comments:
            logger.info(f"Successfully fetched {len(comments)} comments")
            comment = comments[0]
            logger.info(
                f"Sample comment: ID={comment['id']}, Author={comment['author']}"
            )
            logger.info(f"Comment body: {comment['body'][:100]}...")
        else:
            logger.warning(f"No comments found in r/{subreddit}")
    except Exception as e:
        logger.error(f"Error fetching comments: {str(e)}")
        logger.error(traceback.format_exc())
        return False

    # Test posting if requested and we have at least one comment
    if test_posting and comments and client.can_post:
        try:
            test_comment_id = comments[0]["id"]
            logger.info(f"Testing posting a reply to comment {test_comment_id}...")

            # Get user confirmation before posting
            confirm = input("Are you sure you want to post a test comment? (y/n): ")
            if confirm.lower() != "y":
                logger.info("Test posting cancelled by user")
                return True

            result = client.reply_to_comment(
                comment_id=test_comment_id,
                text="This is a test comment from a sentiment analysis app. Please ignore.",
            )

            if result:
                logger.info(f"Successfully posted comment! Comment URL: {result}")
                return True
            else:
                logger.error("Failed to post comment.")
                return False
        except Exception as e:
            logger.error(f"Error posting comment: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Reddit OAuth authentication")
    parser.add_argument(
        "--force-auth", action="store_true", help="Force re-authentication"
    )
    parser.add_argument(
        "--test-posting", action="store_true", help="Test posting a comment"
    )
    parser.add_argument(
        "--subreddit", default="AskReddit", help="Subreddit to fetch comments from"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--manual-auth",
        action="store_true",
        help="Use manual authentication (requires copy/paste of auth code)",
    )
    args = parser.parse_args()

    success = test_oauth_flow(
        force_auth=args.force_auth,
        test_posting=args.test_posting,
        subreddit=args.subreddit,
        verbose=args.verbose,
        manual_auth=args.manual_auth,
    )

    if success:
        logger.info("Test completed successfully")
        sys.exit(0)
    else:
        logger.error("Test failed")
        sys.exit(1)
