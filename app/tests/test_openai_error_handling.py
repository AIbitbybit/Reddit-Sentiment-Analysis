#!/usr/bin/env python3
"""
Test script to verify that OpenAI API error handling works correctly.
"""

import sys
import time
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from src.reddit_sentiment_analysis.utils import check_internet_connectivity
from src.reddit_sentiment_analysis.workflows.sentiment_workflow import (
    CommentState,
    analyze_sentiment,
)


def test_internet_connectivity():
    """Test the internet connectivity check function."""
    print("=== Testing Internet Connectivity Check ===")

    # Check connection to OpenAI
    connectivity, error = check_internet_connectivity(host="api.openai.com")
    print(f"OpenAI API Connection: {'Connected' if connectivity else 'Disconnected'}")
    if error:
        print(f"Error: {error}")

    # Check connection to a non-existent host
    connectivity, error = check_internet_connectivity(
        host="nonexistent-host-xyz.com", timeout=2
    )
    print(
        f"Invalid Host Connection: {'Connected' if connectivity else 'Disconnected (expected)'}"
    )
    if error:
        print(f"Error (expected): {error}")

    return True


def test_sentiment_error_handling():
    """Test that sentiment analysis handles errors gracefully."""
    print("\n=== Testing Sentiment Analysis Error Handling ===")

    # Create a test comment
    state = CommentState(
        comment_id="test_error_handling",
        comment_text="This is a test comment that should be analyzed for sentiment.",
        subreddit="test_subreddit",
        author="test_author",
        permalink="test_permalink",
        created_at=time.time(),
    )

    # Analyze sentiment - this should not crash even with API issues
    try:
        print("Analyzing sentiment...")
        result_state = analyze_sentiment(state)
        print(f"Result: {result_state.sentiment_result}")

        if result_state.sentiment_result:
            print(f"Sentiment: {result_state.sentiment_result['sentiment']}")
            print(f"Confidence: {result_state.sentiment_result['confidence']}")
            print(f"Explanation: {result_state.sentiment_result['explanation']}")
            return True
        else:
            print("No sentiment result returned")
            return False
    except Exception as e:
        print(f"Test failed with exception: {str(e)}")
        return False


if __name__ == "__main__":
    connectivity_test = test_internet_connectivity()
    sentiment_test = test_sentiment_error_handling()
    success = connectivity_test and sentiment_test

    print(f"\nTests {'passed' if success else 'failed'}")
    sys.exit(0 if success else 1)
