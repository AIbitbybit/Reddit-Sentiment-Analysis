#!/usr/bin/env python3
"""
Test script to verify that the CommentState model validator correctly handles AIMessage objects.
"""

import sys
import time
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from langchain_core.messages import AIMessage
from src.reddit_sentiment_analysis.workflows.sentiment_workflow import CommentState


def test_model_validator():
    """Test that the model validator correctly converts AIMessage objects to strings."""
    print("=== Testing CommentState Model Validator ===")

    # Create test data with AIMessage objects
    ai_message = AIMessage(content="This is a test message")

    # Create a CommentState with AIMessage objects
    state = CommentState(
        comment_id="test_id",
        comment_text="This is a test comment",
        subreddit="test_subreddit",
        author="test_author",
        permalink="test_permalink",
        created_at=time.time(),
        response_draft=ai_message,  # This should be auto-converted to string
        final_response=ai_message,  # This should be auto-converted to string
    )

    # Check that the fields were correctly converted to strings
    print(f"Response draft type: {type(state.response_draft)}")
    print(f"Final response type: {type(state.final_response)}")

    is_success = isinstance(state.response_draft, str) and isinstance(
        state.final_response, str
    )

    if is_success:
        print("✅ AIMessage objects were correctly converted to strings!")
        print(f"Response draft: {state.response_draft}")
        print(f"Final response: {state.final_response}")
    else:
        print("❌ Model validator failed to convert AIMessage objects to strings.")
        print(
            f"Types - Response draft: {type(state.response_draft)}, Final response: {type(state.final_response)}"
        )

    return is_success


if __name__ == "__main__":
    success = test_model_validator()
    print(f"\nTest {'passed' if success else 'failed'}")
    sys.exit(0 if success else 1)
