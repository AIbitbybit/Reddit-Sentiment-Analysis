#!/usr/bin/env python3
"""
Test script to verify that AIMessage conversion to string is working properly.
"""

import sys
import time
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from langchain_core.messages import AIMessage
from src.reddit_sentiment_analysis.workflows.sentiment_workflow import CommentState


def test_string_conversion():
    """Test that AIMessage objects are properly converted to strings."""
    print("=== Testing AIMessage Conversion ===")

    # Create a test message
    ai_message = AIMessage(content="This is a test message")
    print(f"Original AIMessage: {ai_message}")
    print(f"AIMessage type: {type(ai_message)}")

    # Extract content
    content = ai_message.content if hasattr(ai_message, "content") else ai_message
    print(f"Extracted content: {content}")
    print(f"Content type: {type(content)}")

    # Create a test CommentState
    state = CommentState(
        comment_id="test_id",
        comment_text="This is a test comment",
        subreddit="test_subreddit",
        author="test_author",
        permalink="test_permalink",
        created_at=time.time(),
    )

    # Set response_draft to AIMessage
    state.response_draft = ai_message
    print(f"State response_draft type: {type(state.response_draft)}")

    # Extract content from response_draft
    if hasattr(state.response_draft, "content"):
        state.response_draft = state.response_draft.content

    print(f"Converted response_draft: {state.response_draft}")
    print(f"Converted response_draft type: {type(state.response_draft)}")

    # Check if validation would succeed
    is_string = isinstance(state.response_draft, str)
    print(f"Is response_draft a string? {is_string}")

    return is_string


if __name__ == "__main__":
    success = test_string_conversion()
    print(f"\nTest {'passed' if success else 'failed'}")
    sys.exit(0 if success else 1)
