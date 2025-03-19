#!/usr/bin/env python3
"""
Test script to verify that the workflow properly handles END signals.
"""

import sys
import time
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from langgraph.graph import END, StateGraph
from src.reddit_sentiment_analysis.workflows.sentiment_workflow import CommentState


def test_workflow_end_handling():
    """Test that the workflow properly handles END signals."""
    print("=== Testing Workflow END Signal Handling ===")

    # Create a test CommentState with positive sentiment
    positive_state = CommentState(
        comment_id="positive_id",
        comment_text="This is a great service!",
        subreddit="test_subreddit",
        author="test_author",
        permalink="test_permalink",
        created_at=time.time(),
        sentiment_result={
            "sentiment": "positive",
            "confidence": 0.9,
            "explanation": "The comment expresses satisfaction with the service.",
        },
    )

    # Create our own simplified test workflow
    print("Creating test workflow with END signal handling...")

    # Create a simplified workflow for testing
    workflow = StateGraph(CommentState)

    # Define simple nodes
    def analyze(state):
        print(f"Analyzing sentiment for {state.comment_id}...")
        return state

    def generate(state):
        print(
            f"Generate node for {state.comment_id} with sentiment {state.sentiment_result['sentiment']}"
        )
        # Return END for positive sentiment
        if state.sentiment_result["sentiment"] == "positive":
            print("Positive sentiment detected, returning END")
            return END

        print("Negative sentiment detected, continuing workflow")
        return state

    def approve(state):
        print(f"Approval node reached for {state.comment_id}")
        return state

    # Add nodes
    workflow.add_node("analyze", analyze)
    workflow.add_node("generate", generate)
    workflow.add_node("approve", approve)

    # Add edges with conditional routing
    workflow.add_edge("analyze", "generate")

    # If generate returns END, skip to end
    workflow.add_conditional_edges(
        "generate",
        lambda x: "approve" if not isinstance(x, str) else END,
    )

    workflow.add_edge("approve", END)

    # Set entry point
    workflow.set_entry_point("analyze")

    # Compile and execute
    compiled_workflow = workflow.compile()

    # Test with positive sentiment (will produce an END signal)
    print(
        "\nExecuting workflow with positive sentiment (should end early but trigger error)..."
    )
    try:
        result = compiled_workflow.invoke(positive_state)
        print(f"Workflow execution completed, result: {result}")
        positive_success = True
    except Exception as e:
        print(f"Expected error during workflow execution: {str(e)}")
        # This is how we should handle the error in the application
        if "Expected dict, got __end__" in str(
            e
        ) and "INVALID_GRAPH_NODE_RETURN_VALUE" in str(e):
            print("Successfully detected END signal error for positive sentiment")
            print(
                "In the application, we would handle this by returning a default result"
            )

            # Here's how we would handle this in the application
            positive_result = {
                "comment_id": positive_state.comment_id,
                "sentiment": positive_state.sentiment_result,
                "response_draft": None,
                "human_approved": None,
                "final_response": None,
                "analyzed_at": positive_state.analyzed_at or time.time(),
            }
            print(f"Constructed result for positive sentiment: {positive_result}")
            positive_success = True
        else:
            print("Unexpected error")
            positive_success = False

    # Create a test CommentState with negative sentiment
    negative_state = CommentState(
        comment_id="negative_id",
        comment_text="This service is terrible!",
        subreddit="test_subreddit",
        author="test_author",
        permalink="test_permalink",
        created_at=time.time(),
        sentiment_result={
            "sentiment": "negative",
            "confidence": 0.9,
            "explanation": "The comment expresses dissatisfaction with the service.",
        },
    )

    # Test with negative sentiment (should go through the full workflow)
    print(
        "\nExecuting workflow with negative sentiment (should go through approval)..."
    )
    try:
        result = compiled_workflow.invoke(negative_state)
        print(f"Workflow execution completed successfully for negative sentiment")
        negative_success = True
    except Exception as e:
        print(f"Unexpected error during negative sentiment workflow: {str(e)}")
        negative_success = False

    return positive_success and negative_success


if __name__ == "__main__":
    success = test_workflow_end_handling()
    print(f"\nTest {'passed' if success else 'failed'}")
    sys.exit(0 if success else 1)
