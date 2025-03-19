"""
LangGraph workflow for sentiment analysis and response generation with human-in-the-loop approval.
"""

import json
import logging
import os
import pickle
import time
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Tuple, Union

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt.tool_executor import ToolExecutor
from pydantic import BaseModel, Field, model_validator

from ..analysis.sentiment_analyzer import SentimentResult
from ..config import OPENAI_CONFIG
from ..response_generator import ResponseGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("reddit_sentiment_analysis.workflows.sentiment_workflow")


# State persistence manager for workflows
class WorkflowStateManager:
    """Manager for persisting and retrieving workflow states."""

    def __init__(self, storage_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the workflow state manager.

        Args:
            storage_dir: Directory to store workflow states
        """
        if storage_dir is None:
            storage_dir = Path("data/workflow_states")

        self.storage_dir = Path(storage_dir)

        # Create directory if it doesn't exist
        os.makedirs(self.storage_dir, exist_ok=True)

        logger.info(f"Initialized workflow state manager at {self.storage_dir}")

    def save_state(self, comment_id: str, state: Any) -> None:
        """
        Save a workflow state for a comment.

        Args:
            comment_id: ID of the comment
            state: Workflow state object
        """
        state_path = self.storage_dir / f"{comment_id}.pkl"

        with open(state_path, "wb") as f:
            pickle.dump(state, f)

        logger.info(f"Saved workflow state for comment {comment_id}")

    def load_state(self, comment_id: str) -> Optional[Any]:
        """
        Load a workflow state for a comment.

        Args:
            comment_id: ID of the comment

        Returns:
            Workflow state object or None if not found
        """
        state_path = self.storage_dir / f"{comment_id}.pkl"

        if not state_path.exists():
            logger.warning(f"No workflow state found for comment {comment_id}")
            return None

        with open(state_path, "rb") as f:
            state = pickle.load(f)

        logger.info(f"Loaded workflow state for comment {comment_id}")
        return state

    def delete_state(self, comment_id: str) -> bool:
        """
        Delete a workflow state for a comment.

        Args:
            comment_id: ID of the comment

        Returns:
            True if the state was deleted, False otherwise
        """
        state_path = self.storage_dir / f"{comment_id}.pkl"

        if not state_path.exists():
            return False

        os.remove(state_path)
        logger.info(f"Deleted workflow state for comment {comment_id}")
        return True


# Global workflow state manager instance
workflow_state_manager = WorkflowStateManager()


# Define state schemas
class CommentState(BaseModel):
    """State for comment analysis workflow."""

    # Input
    comment_id: str = Field(description="The ID of the comment being analyzed")
    comment_text: str = Field(description="The text content of the comment")
    subreddit: str = Field(description="The subreddit where the comment was posted")
    author: str = Field(description="The author of the comment")
    permalink: str = Field(description="The permalink to the comment")

    # Analysis state
    sentiment_result: Optional[Dict[str, Any]] = Field(
        default=None, description="Result of sentiment analysis"
    )
    response_draft: Optional[str] = Field(
        default=None, description="Draft response to the comment"
    )
    human_approved: Optional[bool] = Field(
        default=None, description="Whether the response was approved by a human"
    )
    final_response: Optional[str] = Field(
        default=None, description="Final approved response"
    )

    # Metadata
    created_at: float = Field(
        description="When the comment was created (UTC timestamp)"
    )
    analyzed_at: Optional[float] = Field(
        default=None, description="When the analysis was performed"
    )

    @model_validator(mode="before")
    @classmethod
    def extract_ai_message_content(cls, data):
        """Extract content from AIMessage objects."""
        # Handle response_draft
        if "response_draft" in data and data["response_draft"] is not None:
            if hasattr(data["response_draft"], "content"):
                logger.info(f"Converting AIMessage to string for response_draft")
                data["response_draft"] = data["response_draft"].content

        # Handle final_response
        if "final_response" in data and data["final_response"] is not None:
            if hasattr(data["final_response"], "content"):
                logger.info(f"Converting AIMessage to string for final_response")
                data["final_response"] = data["final_response"].content

        return data


def analyze_sentiment(state: CommentState) -> CommentState:
    """Analyze the sentiment of the comment."""
    logger.info(f"Analyzing sentiment for comment {state.comment_id}")

    try:
        # Initialize LLM with retry settings
        llm = ChatOpenAI(
            temperature=0.0,
            max_retries=OPENAI_CONFIG["max_retries"],
            request_timeout=OPENAI_CONFIG["timeout"],
        )

        # Create sentiment analysis prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a sentiment analysis expert. Analyze the sentiment of the given text and classify it as positive, negative, or neutral.
            
Provide a confidence score between 0 and 1, where:
- 0.0-0.4: Low confidence
- 0.4-0.7: Medium confidence
- 0.7-1.0: High confidence

Consider the context of business and product reviews when analyzing.
If the text contains mixed sentiments, focus on the predominant sentiment.

Format your response as a JSON object with:
- sentiment: The sentiment classification (positive, negative, or neutral)
- confidence: A float between 0 and 1
- explanation: A brief explanation of your classification""",
                ),
                ("user", "{text}"),
            ]
        )

        # Create output parser
        output_parser = JsonOutputParser(pydantic_object=SentimentResult)

        # Create and execute chain
        chain = prompt | llm | output_parser

        # Add timeout and retry logic for OpenAI API calls
        try:
            result = chain.invoke({"text": state.comment_text})
        except Exception as api_error:
            logger.error(f"OpenAI API error: {str(api_error)}")
            # Provide a fallback result
            result = {
                "sentiment": "neutral",
                "confidence": 0.5,
                "explanation": f"Failed to analyze due to API error: {str(api_error)[:100]}...",
            }

        # Update state
        state.sentiment_result = result
        state.analyzed_at = time.time()

        logger.info(
            f"Comment {state.comment_id} sentiment: {result['sentiment']} (confidence: {result['confidence']:.2f})"
        )
        return state
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        # Provide a fallback result
        state.sentiment_result = {
            "sentiment": "neutral",
            "confidence": 0.5,
            "explanation": f"Failed to analyze due to error: {str(e)[:100]}...",
        }
        state.analyzed_at = time.time()
        return state


def generate_response(state: CommentState) -> CommentState:
    """Generate a response to a negative comment."""
    # Only generate responses for negative comments
    if (
        not state.sentiment_result
        or state.sentiment_result.get("sentiment") != "negative"
    ):
        logger.info(
            f"No response generated for comment {state.comment_id} (not negative)"
        )
        # Return "END" to signal we want to end the workflow early
        return END

    try:
        logger.info(f"Generating response to negative comment {state.comment_id}")

        # Create a response generator with fallback option
        response_generator = ResponseGenerator()

        # Generate response
        response = response_generator.generate_response(
            comment_text=state.comment_text,
            sentiment_result=state.sentiment_result,
            author=state.author,
            subreddit=state.subreddit,
        )

        logger.info(f"Generated response for comment {state.comment_id}")

        # Handle different response types (AIMessage or string)
        if hasattr(response, "content"):
            logger.info(f"Response is an AIMessage object, extracting content")
            # Log the response type and first part of the content
            logger.info(f"Response type: {type(response)}")
            logger.info(
                f"Response content (first 100 chars): {str(response.content)[:100]}"
            )
            state.response_draft = response.content
        else:
            # Already a string
            logger.info(f"Response is a string, using directly")
            state.response_draft = response

        # Ensure response_draft is a string
        if state.response_draft is not None:
            state.response_draft = str(state.response_draft)

        return state
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")

        # Provide a fallback response
        state.response_draft = (
            "I noticed your concerns and would like to help. "
            "Please contact our customer service team for assistance."
        )
        return state


def human_approval(state: CommentState) -> Union[CommentState, str]:
    """Wait for human approval of the response through the GUI."""
    if not state.response_draft:
        return END

    logger.info(f"Response to comment {state.comment_id} ready for review in GUI")

    # The response will be reviewed and approved/rejected through the GUI
    # The state will be updated when the user takes action in the interface
    # For now, we'll set it to None to indicate pending approval
    state.human_approved = None
    return state


def finalize_response(state: CommentState) -> CommentState:
    """Finalize the response based on GUI approval."""
    if not state.human_approved:
        logger.info(f"Response to comment {state.comment_id} was not approved via GUI")
        return state

    logger.info(f"Finalizing GUI-approved response to comment {state.comment_id}")

    # Set the final response
    state.final_response = state.response_draft
    return state


def create_sentiment_workflow() -> StateGraph:
    """Create a workflow for sentiment analysis and response generation."""
    # Create workflow
    workflow = StateGraph(CommentState)

    # Add nodes
    workflow.add_node("analyze", analyze_sentiment)
    workflow.add_node("generate", generate_response)
    workflow.add_node("approve", human_approval)
    workflow.add_node("finalize", finalize_response)

    # Define edges with conditional routing
    workflow.add_edge("analyze", "generate")

    # If generate_response returns END (non-negative sentiment), skip to end
    workflow.add_conditional_edges(
        "generate",
        lambda x: "approve" if not isinstance(x, str) else END,
    )

    workflow.add_edge("approve", "finalize")
    workflow.add_edge("finalize", END)

    # Set entry point
    workflow.set_entry_point("analyze")

    return workflow


async def process_comment(comment_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single comment through the sentiment workflow.

    Args:
        comment_data: Dictionary containing comment data

    Returns:
        Dictionary containing analysis results and response if applicable
    """
    # Create initial state
    initial_state = CommentState(
        comment_id=comment_data["id"],
        comment_text=comment_data["body"],
        subreddit=comment_data["subreddit"],
        author=comment_data["author"],
        permalink=comment_data["permalink"],
        created_at=comment_data["created_utc"],
    )

    try:
        # Create and run workflow
        workflow = create_sentiment_workflow()
        app = workflow.compile()
        final_state = await app.ainvoke(initial_state)

        # Handle the response - check if it's a dictionary (AddableValuesDict)
        response_draft = None
        final_response = None

        # Different handling based on what type final_state is
        if hasattr(final_state, "response_draft"):
            # It's a CommentState object
            response_draft = final_state.response_draft
            final_response = final_state.final_response

            # Handle AIMessage objects for response_draft
            if response_draft is not None:
                if hasattr(response_draft, "content"):
                    logger.info(f"Converting AIMessage to string for response_draft")
                    response_draft = response_draft.content
                response_draft = str(response_draft)

            # Handle AIMessage objects for final_response
            if final_response is not None:
                if hasattr(final_response, "content"):
                    logger.info(f"Converting AIMessage to string for final_response")
                    final_response = final_response.content
                final_response = str(final_response)

            human_approved = final_state.human_approved
            sentiment_result = final_state.sentiment_result
            analyzed_at = final_state.analyzed_at
            comment_id = final_state.comment_id
        else:
            # It's an AddableValuesDict or similar
            logger.info(f"Processing non-CommentState result: {type(final_state)}")

            # Extract values from the dictionary
            try:
                # Try dictionary-style access
                response_draft = final_state.get("response_draft")
                final_response = final_state.get("final_response")
                human_approved = final_state.get("human_approved")
                sentiment_result = final_state.get("sentiment_result")
                analyzed_at = final_state.get("analyzed_at")
                comment_id = comment_data["id"]  # Fallback to original data

                # Handle AIMessage objects for response_draft
                if response_draft is not None:
                    if hasattr(response_draft, "content"):
                        logger.info(
                            f"Converting AIMessage to string for response_draft"
                        )
                        response_draft = response_draft.content
                    response_draft = str(response_draft)

                # Handle AIMessage objects for final_response
                if final_response is not None:
                    if hasattr(final_response, "content"):
                        logger.info(
                            f"Converting AIMessage to string for final_response"
                        )
                        final_response = final_response.content
                    final_response = str(final_response)
            except Exception as access_error:
                logger.warning(
                    f"Error accessing fields from final_state: {access_error}"
                )
                # Fallback to providing empty values
                human_approved = None
                sentiment_result = final_state
                analyzed_at = time.time()
                comment_id = comment_data["id"]

        # Store workflow state if human approval is needed
        if human_approved is None and response_draft:
            try:
                workflow_state_manager.save_state(comment_data["id"], initial_state)
                logger.info(
                    f"Stored workflow state for comment {comment_data['id']} awaiting human approval"
                )
            except Exception as save_error:
                logger.error(f"Error saving workflow state: {save_error}")

        # Return results with properly extracted string content
        return {
            "comment_id": comment_id,
            "sentiment": sentiment_result,
            "response_draft": response_draft,
            "human_approved": human_approved,
            "final_response": final_response,
            "analyzed_at": analyzed_at,
        }
    except Exception as e:
        if "INVALID_GRAPH_NODE_RETURN_VALUE" in str(
            e
        ) and "Expected dict, got __end__" in str(e):
            # This happens when the comment is not negative and the workflow ends early
            logger.info(
                f"Workflow ended early for comment {comment_data['id']} (not negative)"
            )
            return {
                "comment_id": comment_data["id"],
                "sentiment": {
                    "sentiment": "non-negative",
                    "confidence": 0.0,
                    "explanation": "Comment was determined to be non-negative",
                },
                "response_draft": None,
                "human_approved": None,
                "final_response": None,
                "analyzed_at": time.time(),
            }
        else:
            # Some other error occurred
            logger.error(f"Error in workflow processing: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            # Return a minimal result with error info
            return {
                "comment_id": comment_data["id"],
                "sentiment": {
                    "sentiment": "unknown",
                    "confidence": 0.0,
                    "explanation": f"Error: {str(e)}",
                },
                "response_draft": "I noticed your concerns and would like to help. Please contact our customer service team for assistance.",
                "human_approved": None,
                "final_response": None,
                "analyzed_at": time.time(),
                "error": str(e),
            }


async def resume_workflow_after_approval(
    comment_id: str, approved: bool
) -> Optional[Dict[str, Any]]:
    """
    Resume a workflow that was waiting for human approval.

    Args:
        comment_id: ID of the comment
        approved: Whether the response was approved

    Returns:
        Updated workflow state or None if state couldn't be found/resumed
    """
    # Load the saved state
    state = workflow_state_manager.load_state(comment_id)
    if not state:
        logger.error(f"Could not find saved workflow state for comment {comment_id}")
        return None

    # Update the human approval field
    state.human_approved = approved
    logger.info(
        f"Updated workflow state for comment {comment_id} with approval={approved}"
    )

    try:
        # Create a new workflow and resume it from the current state
        workflow = create_sentiment_workflow()
        app = workflow.compile()

        # Resume workflow from the approve node
        final_state = await app.ainvoke(state, dataflow="finalize")

        # Handle the response - check if it's a dictionary (AddableValuesDict)
        response_draft = None
        final_response = None

        # Different handling based on what type final_state is
        if hasattr(final_state, "response_draft"):
            # It's a CommentState object
            response_draft = final_state.response_draft
            final_response = final_state.final_response

            # Handle AIMessage objects for response_draft
            if response_draft is not None:
                if hasattr(response_draft, "content"):
                    logger.info(f"Converting AIMessage to string for response_draft")
                    response_draft = response_draft.content
                response_draft = str(response_draft)

            # Handle AIMessage objects for final_response
            if final_response is not None:
                if hasattr(final_response, "content"):
                    logger.info(f"Converting AIMessage to string for final_response")
                    final_response = final_response.content
                final_response = str(final_response)

            human_approved = final_state.human_approved
            sentiment_result = final_state.sentiment_result
            analyzed_at = final_state.analyzed_at
        else:
            # It's an AddableValuesDict or similar
            logger.info(f"Processing non-CommentState result: {type(final_state)}")

            # Extract values from the dictionary
            try:
                # Try dictionary-style access
                response_draft = final_state.get("response_draft")
                final_response = final_state.get("final_response")
                human_approved = final_state.get("human_approved")
                sentiment_result = final_state.get("sentiment_result")
                analyzed_at = final_state.get("analyzed_at")

                # Handle AIMessage objects for response_draft
                if response_draft is not None:
                    if hasattr(response_draft, "content"):
                        logger.info(
                            f"Converting AIMessage to string for response_draft"
                        )
                        response_draft = response_draft.content
                    response_draft = str(response_draft)

                # Handle AIMessage objects for final_response
                if final_response is not None:
                    if hasattr(final_response, "content"):
                        logger.info(
                            f"Converting AIMessage to string for final_response"
                        )
                        final_response = final_response.content
                    final_response = str(final_response)
            except Exception as access_error:
                logger.warning(
                    f"Error accessing fields from final_state: {access_error}"
                )
                # Use values from original state
                response_draft = state.response_draft
                final_response = state.response_draft if approved else None
                human_approved = approved
                sentiment_result = state.sentiment_result
                analyzed_at = time.time()

        # Clean up the stored state
        workflow_state_manager.delete_state(comment_id)

        # Return the final state with properly extracted string content
        return {
            "comment_id": comment_id,
            "sentiment": sentiment_result,
            "response_draft": response_draft,
            "human_approved": human_approved,
            "final_response": final_response,
            "analyzed_at": analyzed_at,
        }
    except Exception as e:
        logger.error(f"Error resuming workflow: {str(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")

        # Return the state as it was, with approval updated
        return {
            "comment_id": comment_id,
            "sentiment": state.sentiment_result,
            "response_draft": state.response_draft,
            "human_approved": approved,
            "final_response": state.response_draft if approved else None,
            "analyzed_at": time.time(),
            "error": str(e),
        }
