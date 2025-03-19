#!/usr/bin/env python3
"""
Test basic functionality of the Reddit Sentiment Analysis application.
This script tests core functionality without external dependencies like SMTP/email.
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("basic_function_test")

# Add import paths
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir.parent))

# Import application modules
from app.src.reddit_sentiment_analysis.analysis.sentiment_analyzer import (
    SentimentAnalyzer,
)
from app.src.reddit_sentiment_analysis.storage.comment_db import CommentDatabase
from app.src.reddit_sentiment_analysis.workflows.sentiment_workflow import (
    CommentState,
    analyze_sentiment,
    generate_response,
)


async def test_sentiment_analysis():
    """Test the sentiment analysis functionality."""
    print("\n=== Testing Sentiment Analysis ===")

    # Create test texts with different sentiments
    test_texts = [
        "I absolutely love this product! It's amazing and works perfectly.",
        "This service is terrible. I'm very disappointed with the quality.",
        "The product works as expected. It meets the requirements.",
    ]

    # Create analyzer
    analyzer = SentimentAnalyzer()

    # Analyze each text
    for i, text in enumerate(test_texts):
        print(f"\nAnalyzing text {i+1}: {text[:30]}...")
        try:
            result = await analyzer.analyze_sentiment(text)
            print(f"Sentiment: {result['sentiment']}")
            print(f"Confidence: {result['confidence']:.2f}")
            print(f"Explanation: {result['explanation']}")
        except Exception as e:
            print(f"Error analyzing text: {str(e)}")

    return True


async def test_workflow_functions():
    """Test the workflow functions directly."""
    print("\n=== Testing Workflow Functions ===")

    # Create a test comment state
    comment_state = CommentState(
        comment_id="test_workflow_id",
        comment_text="I'm really disappointed with the service. It doesn't work as advertised.",
        subreddit="TestSubreddit",
        author="test_user",
        permalink="/r/TestSubreddit/comments/abc123/test_post/def456/",
        created_at=time.time(),
    )

    print(f"Processing test comment: {comment_state.comment_text[:30]}...")

    try:
        # Analyze sentiment
        print("Analyzing sentiment...")
        updated_state = analyze_sentiment(comment_state)

        print(f"Sentiment: {updated_state.sentiment_result['sentiment']}")
        print(f"Confidence: {updated_state.sentiment_result['confidence']:.2f}")
        print(f"Explanation: {updated_state.sentiment_result['explanation']}")

        # Generate response
        print("\nGenerating response...")
        result = generate_response(updated_state)

        if isinstance(result, str) and result == "END":
            print("Workflow ended early (non-negative sentiment)")
            return True

        updated_state = result
        print(
            f"Response draft generated: {str(updated_state.response_draft)[:100]}..."
            if updated_state.response_draft
            else "No response generated"
        )

        return True
    except Exception as e:
        print(f"Error in workflow functions: {str(e)}")
        return None


async def test_database():
    """Test database operations."""
    print("\n=== Testing Database Operations ===")

    # Create database directory
    os.makedirs("data", exist_ok=True)

    # Create test database
    db = CommentDatabase("data/test_comments.db")

    # Create test comment
    comment_data = {
        "id": "test_db_id",
        "comment_id": "reddit_comment_id",
        "subreddit": "TestSubreddit",
        "author": "test_user",
        "body": "This is a test comment for database operations.",
        "created_utc": time.time(),
        "permalink": "/r/TestSubreddit/comments/abc123/test_post/def456/",
    }

    # Add to database
    print("Adding comment to database...")
    db_id = db.add_comment(
        comment_data=comment_data,
        key_term="test",
        sentiment="negative",
        confidence=0.85,
        ai_response="This is a test response.",
        status="pending_approval",
    )

    print(f"Comment added with ID: {db_id}")

    # Retrieve from database
    print("Retrieving comment from database...")
    retrieved = db.get_comment(db_id)

    if retrieved:
        print(f"Retrieved comment: {retrieved['body'][:30]}...")
        print(f"Status: {retrieved['status']}")

        # Update status
        print("Updating comment status...")
        updated = db.update_comment_status(db_id, "approved")

        if updated:
            # Get updated comment
            updated_comment = db.get_comment(db_id)
            print(f"New status: {updated_comment['status']}")

            # Update email sent status
            print("Updating email sent status...")
            email_recipient = "test@example.com"
            email_sent = db.mark_email_sent(db_id, email_recipient)

            if email_sent:
                final_comment = db.get_comment(db_id)
                print(f"Final status: {final_comment['status']}")
                print(f"Email sent: {final_comment['email_sent'] == 1}")
                print(f"Email recipient: {final_comment['email_recipient']}")
            else:
                print("Failed to update email sent status")
        else:
            print("Failed to update comment status")
    else:
        print("Failed to retrieve comment from database")

    return True


async def main():
    """Run all basic function tests."""
    print("=" * 80)
    print("REDDIT SENTIMENT ANALYSIS - BASIC FUNCTIONALITY TESTS".center(80))
    print("=" * 80)

    # Create a directory for test data if it doesn't exist
    data_dir = Path("data")
    os.makedirs(data_dir, exist_ok=True)
    workflow_states_dir = Path("data/workflow_states")
    os.makedirs(workflow_states_dir, exist_ok=True)

    # Run tests
    tests = [
        ("Sentiment Analysis", test_sentiment_analysis),
        ("Workflow Functions", test_workflow_functions),
        ("Database Operations", test_database),
    ]

    results = {}

    for name, test_func in tests:
        print(f"\n{'=' * 40}")
        print(f"Running {name} Test")
        print(f"{'=' * 40}")

        try:
            start_time = time.time()
            result = await test_func()
            elapsed = time.time() - start_time

            if result:
                print(f"\n✅ {name} Test PASSED in {elapsed:.2f} seconds")
                results[name] = "PASS"
            else:
                print(f"\n❌ {name} Test FAILED in {elapsed:.2f} seconds")
                results[name] = "FAIL"
        except Exception as e:
            print(f"\n❌ {name} Test ERROR: {str(e)}")
            results[name] = "ERROR"

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY".center(80))
    print("=" * 80)

    for name, result in results.items():
        print(f"{name}: {result}")

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED".center(80))
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
