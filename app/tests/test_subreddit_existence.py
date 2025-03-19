#!/usr/bin/env python3
"""
Test script to check if the configured subreddits exist.
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(app_dir))

from src.reddit_sentiment_analysis.config import DEFAULT_SUBREDDITS

# Import the necessary components
from src.reddit_sentiment_analysis.data_collection.reddit_client import RedditClient


def test_subreddit_existence():
    """Test if the configured subreddits exist."""
    print("=" * 80)
    print("SUBREDDIT EXISTENCE TEST".center(80))
    print("=" * 80)

    print(f"\nChecking if these subreddits exist: {', '.join(DEFAULT_SUBREDDITS)}")

    # Initialize Reddit client
    reddit_client = RedditClient()

    # Check each subreddit
    valid_subreddits = []
    invalid_subreddits = []

    for subreddit_name in DEFAULT_SUBREDDITS:
        print(f"\nChecking r/{subreddit_name}...", end=" ")
        try:
            subreddit = reddit_client.reddit.subreddit(subreddit_name)
            # Try to access a property to verify it exists
            title = subreddit.title
            subscribers = subreddit.subscribers

            print(f"✅ EXISTS - Title: {title} | Subscribers: {subscribers:,}")
            valid_subreddits.append(subreddit_name)
        except Exception as e:
            print(f"❌ DOES NOT EXIST - Error: {str(e)}")
            invalid_subreddits.append(subreddit_name)

    print("\n" + "=" * 80)
    print("RESULTS".center(80))
    print("=" * 80)

    print(f"\nValid subreddits ({len(valid_subreddits)}):")
    for subreddit in valid_subreddits:
        print(f"- r/{subreddit}")

    print(f"\nInvalid subreddits ({len(invalid_subreddits)}):")
    for subreddit in invalid_subreddits:
        print(f"- r/{subreddit}")

    print("\nRECOMMENDATION:")
    if invalid_subreddits:
        print(
            "Update the DEFAULT_SUBREDDITS list in config.py to remove these subreddits:"
        )
        for subreddit in invalid_subreddits:
            print(f"- r/{subreddit}")
    else:
        print("All configured subreddits exist. No changes needed.")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        test_subreddit_existence()
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback

        traceback.print_exc()
