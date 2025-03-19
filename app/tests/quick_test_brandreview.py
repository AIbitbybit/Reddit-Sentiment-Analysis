#!/usr/bin/env python3
"""
Quick test to verify that the BrandReview subreddit doesn't exist.
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(app_dir))

# Import the necessary components
from src.reddit_sentiment_analysis.data_collection.reddit_client import RedditClient


def test_brandreview():
    """Test if BrandReview subreddit exists."""
    print("Testing if r/BrandReview exists...")

    # Initialize Reddit client
    reddit_client = RedditClient()

    # Check the subreddit
    subreddit_name = "BrandReview"
    try:
        subreddit = reddit_client.reddit.subreddit(subreddit_name)
        # Try to access a property to verify it exists
        title = subreddit.title
        subscribers = subreddit.subscribers

        print(f"r/BrandReview EXISTS - Title: {title} | Subscribers: {subscribers:,}")
        return True
    except Exception as e:
        print(f"r/BrandReview DOES NOT EXIST - Error: {str(e)}")
        return False


if __name__ == "__main__":
    try:
        test_brandreview()
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback

        traceback.print_exc()
