#!/usr/bin/env python3
"""
Test script to verify Reddit API functionality.
Run this script to diagnose issues with Reddit API connection and comment retrieval.
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add the app directory to the Python path
app_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(app_dir))

from src.reddit_sentiment_analysis.config import DEFAULT_SUBREDDITS
from src.reddit_sentiment_analysis.data_collection.collector import DataCollector

# Import the necessary components
from src.reddit_sentiment_analysis.data_collection.reddit_client import RedditClient


async def test_reddit_api():
    """
    Test the Reddit API functionality.
    """
    print("=" * 80)
    print("REDDIT API TEST".center(80))
    print("=" * 80)

    # 1. Test Reddit client initialization
    print("\n1. Testing Reddit client initialization...")
    try:
        reddit_client = RedditClient()
        print("✅ Successfully initialized RedditClient")

        # Log client details
        print(
            f"   Client ID: {'*' * 5}{reddit_client.client_id[-3:] if reddit_client.client_id else 'None'}"
        )
        print(f"   User Agent: {reddit_client.user_agent}")

    except Exception as e:
        print(f"❌ Failed to initialize RedditClient: {e}")
        return False

    # 2. Test fetching a subreddit
    print("\n2. Testing subreddit access...")
    try:
        # Use a popular subreddit that's likely to have activity
        test_subreddit = "AskReddit"
        subreddit = reddit_client.reddit.subreddit(test_subreddit)
        print(f"✅ Successfully accessed r/{test_subreddit}")

        # Try to get some basic info
        try:
            sub_title = subreddit.title
            subscribers = subreddit.subscribers
            print(f"   Title: {sub_title}")
            print(f"   Subscribers: {subscribers:,}")
        except Exception as e:
            print(f"   Note: Could not get subreddit details: {e}")

    except Exception as e:
        print(f"❌ Failed to access subreddit: {e}")
        print("   This might indicate Reddit API authentication issues")

    # 3. Test fetching recent comments
    print("\n3. Testing comment retrieval...")
    try:
        # First try a very active subreddit
        print(f"   Trying to fetch 10 recent comments from r/AskReddit...")
        comments = reddit_client.get_recent_comments(subreddit="AskReddit", limit=10)

        if comments:
            print(
                f"✅ Successfully retrieved {len(comments)} comments from r/AskReddit"
            )
            # Show sample of first comment
            if len(comments) > 0:
                comment = comments[0]
                print(f"   Sample comment: Author={comment['author']}")
                print(f"   Text: {comment['body'][:100]}...")
                print(
                    f"   Created at: {datetime.fromtimestamp(comment['created_utc']).strftime('%Y-%m-%d %H:%M:%S')}"
                )
        else:
            print("❌ No comments retrieved from r/AskReddit")

        # Now test with configured subreddits
        print(
            f"\n   Testing with configured subreddits: {', '.join(DEFAULT_SUBREDDITS)}"
        )
        for subreddit in DEFAULT_SUBREDDITS:
            print(f"   Fetching comments from r/{subreddit}...")
            comments = reddit_client.get_recent_comments(subreddit=subreddit, limit=10)

            if comments:
                print(f"✅ Retrieved {len(comments)} comments from r/{subreddit}")
            else:
                print(f"❌ No comments retrieved from r/{subreddit}")

    except Exception as e:
        print(f"❌ Failed to retrieve comments: {e}")

    # 4. Test the DataCollector
    print("\n4. Testing DataCollector and comment search...")
    try:
        collector = DataCollector(reddit_client=reddit_client)
        print("✅ Successfully initialized DataCollector")

        # Test with a common key term that should appear in comments
        print("   Testing with a common key term 'help' in r/AskReddit...")
        comments = await collector.get_new_comments(
            key_term="help",
            subreddits=["AskReddit"],
            time_limit=3600,  # Look back 1 hour
        )

        if comments:
            print(f"✅ Found {len(comments)} comments containing 'help' in r/AskReddit")
            # Show a sample comment
            if len(comments) > 0:
                comment = comments[0]
                print(f"   Sample matching comment: Author={comment['author']}")
                print(f"   Text: {comment['body'][:100]}...")
        else:
            print("❌ No comments containing 'help' found in r/AskReddit")
            print("   This is unusual and might indicate an API or search issue")

        # Now test with configured key term and subreddits
        print("\n   Testing with user's configured settings...")
        print("   Please enter your key term to test (e.g., your company name):")
        key_term = input("   > ")

        if not key_term:
            key_term = "business"  # Default fallback term
            print(f"   Using default term: {key_term}")

        print(f"   Searching for '{key_term}' in {', '.join(DEFAULT_SUBREDDITS)}...")
        print(f"   Looking back 24 hours...")

        comments = await collector.get_new_comments(
            key_term=key_term,
            subreddits=DEFAULT_SUBREDDITS,
            time_limit=86400,  # 24 hours
        )

        if comments:
            print(f"✅ Found {len(comments)} comments containing '{key_term}'")
            # Show sample comments
            for i, comment in enumerate(comments[:3]):
                print(
                    f"   Match {i+1}: r/{comment['subreddit']} - u/{comment['author']}"
                )
                print(f"   Text: {comment['body'][:100]}...")
                print()
        else:
            print(f"❌ No comments containing '{key_term}' found in the last 24 hours")
            print("   This could mean:")
            print("   1. The term is not mentioned in these subreddits")
            print("   2. The Reddit API rate limits are being reached")
            print("   3. There's an authentication or permission issue")

    except Exception as e:
        print(f"❌ Failed during DataCollector test: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 80)
    print("TEST COMPLETED".center(80))
    print("=" * 80)

    return True


if __name__ == "__main__":
    try:
        # Run the test
        asyncio.run(test_reddit_api())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        logger.error(f"Error running Reddit API test: {str(e)}")
        import traceback

        traceback.print_exc()
