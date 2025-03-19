"""
Reddit monitoring system with LangGraph-based sentiment analysis.
"""

import asyncio
import logging
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional

from .analysis.sentiment_analyzer import SentimentAnalyzer
from .config import REFRESH_INTERVAL_MINUTES
from .data_collection.collector import DataCollector
from .email_service import EmailService
from .storage.comment_db import CommentDatabase
from .utils import check_internet_connectivity
from .workflows.sentiment_workflow import (
    process_comment,
    resume_workflow_after_approval,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("reddit_sentiment_analysis.monitoring")


class RedditMonitor:
    """Monitor Reddit for new comments and analyze sentiment."""

    def __init__(
        self,
        key_term: str,
        email: str,
        subreddits: Optional[List[str]] = None,
        db: Optional[CommentDatabase] = None,
    ):
        """
        Initialize the Reddit monitor.

        Args:
            key_term: Term to search for
            email: Email address for notifications
            subreddits: List of subreddits to monitor
            db: Comment database (optional, will create new one if not provided)
        """
        self.key_term = key_term
        self.email = email
        self.subreddits = subreddits or ["business", "smallbusiness"]

        # Initialize components
        self.collector = DataCollector()
        self.db = db or CommentDatabase()
        self.email_service = EmailService()

        logger.info(
            f"Initialized Reddit monitor for term '{key_term}' in subreddits: {', '.join(self.subreddits)}"
        )

    async def process_comment(self, comment: Dict) -> Dict:
        """
        Process a single comment through the sentiment workflow.

        Args:
            comment: Comment data dictionary

        Returns:
            Processed comment with analysis results
        """
        try:
            # Process comment through LangGraph workflow
            logger.info(f"Processing comment through workflow: {comment['id']}")
            result = await process_comment(comment)

            # Check if we have sentiment results
            if not result.get("sentiment"):
                logger.warning(f"No sentiment results for comment {comment['id']}")
                return comment

            # Ensure permalink has full Reddit domain
            permalink = comment["permalink"]
            if permalink and not permalink.startswith("http"):
                permalink = f"https://www.reddit.com{permalink}"
            else:
                permalink = comment["permalink"]

            # Ensure response_draft is a string (handle AIMessage objects)
            response_draft = result.get("response_draft")
            if response_draft is not None:
                # Check if it's an object with a content attribute (like AIMessage)
                if hasattr(response_draft, "content"):
                    logger.info(
                        f"Converting AIMessage to string for comment {comment['id']}"
                    )
                    response_draft = response_draft.content
                # Ensure it's a string
                response_draft = str(response_draft)
                logger.info(f"Response draft (truncated): {response_draft[:100]}...")

            # Store results in database
            try:
                self.db.add_comment(
                    comment_data=comment,
                    key_term=self.key_term,
                    sentiment=result["sentiment"]["sentiment"],
                    confidence=result["sentiment"]["confidence"],
                    ai_response=response_draft,
                    status="pending_approval",
                )
                logger.info(f"Stored comment {comment['id']} in database")
            except Exception as db_error:
                logger.error(f"Error storing comment in database: {str(db_error)}")
                import traceback

                logger.error(f"Traceback: {traceback.format_exc()}")

            # Send email for negative comments
            if result["sentiment"]["sentiment"] == "negative" and response_draft:
                try:
                    email_sent = await self.email_service.send_alert(
                        recipient=self.email,
                        comment_data=comment,
                        sentiment_result=result["sentiment"],
                        suggested_response=response_draft,
                    )

                    if email_sent:
                        logger.info(
                            f"Sent email alert for negative comment {comment['id']} to {self.email}"
                        )
                        # Update database to mark email as sent
                        try:
                            self.db.mark_email_sent(comment["id"], self.email)
                            logger.info(
                                f"Updated database to mark email as sent for comment {comment['id']}"
                            )
                        except Exception as db_error:
                            logger.error(
                                f"Error updating email sent status in database: {str(db_error)}"
                            )
                    else:
                        logger.warning(
                            f"Failed to send email alert for negative comment {comment['id']}. Check email settings."
                        )
                except Exception as email_error:
                    logger.error(f"Error sending email alert: {str(email_error)}")
                    import traceback

                    logger.error(f"Email error traceback: {traceback.format_exc()}")

            return result
        except Exception as e:
            logger.error(f"Error processing comment: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return original comment with error info
            comment["error"] = str(e)
            return comment

    async def check_for_new_comments(self) -> List[Dict]:
        """
        Check for new comments about the key term.

        Returns:
            List of processed comments
        """
        try:
            logger.info(
                f"Checking for new comments containing '{self.key_term}' in {self.subreddits}"
            )

            # Check internet connectivity before making API calls
            connectivity, error = check_internet_connectivity(host="api.openai.com")
            if not connectivity:
                logger.error(f"No connection to OpenAI API: {error}")
                logger.info("Skipping comment processing due to connectivity issues")
                return []

            # Collect new comments - use a longer time window (24 hours) to ensure we get results
            logger.info(f"Using time window of 24 hours (86400 seconds)")
            comments = await self.collector.get_new_comments(
                self.key_term, self.subreddits, time_limit=86400
            )

            if not comments:
                logger.info("No new comments found")
                return []

            logger.info(f"Found {len(comments)} new comments")

            # Log details of each found comment
            for i, comment in enumerate(comments):
                logger.info(
                    f"Comment {i+1}/{len(comments)}: ID={comment['id']}, Subreddit={comment['subreddit']}, "
                    f"Author={comment['author']}, Created={datetime.fromtimestamp(comment['created_utc'])}"
                )
                logger.info(f"Comment text: {comment['body'][:100]}...")

            # Process each comment through the workflow
            processed_comments = []
            for comment in comments:
                # Make sure we check for comment existence properly
                # Reddit comment IDs might come with or without the t1_ prefix
                comment_id = comment["id"]

                # Log the comment ID for debugging
                logger.info(f"Checking if comment exists in database: {comment_id}")

                # Check database directly to get a count of entries
                exists_in_db = self.db.comment_exists(comment_id)

                if not exists_in_db:
                    logger.info(
                        f"Comment {comment_id} does not exist in database, processing now"
                    )
                    logger.info(
                        f"Processing comment: Subreddit={comment['subreddit']}, Author={comment['author']}"
                    )
                    logger.info(f"Comment text: {comment['body']}")
                    result = await self.process_comment(comment)
                    processed_comments.append(result)
                else:
                    logger.info(
                        f"Comment {comment_id} already exists in database, skipping"
                    )

            if processed_comments:
                logger.info(
                    f"Successfully processed {len(processed_comments)} new comments"
                )
            else:
                logger.info(
                    "No new comments were processed (all were already in the database)"
                )

            return processed_comments
        except Exception as e:
            logger.error(f"Error checking for new comments: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def handle_response_approval(self, comment_id: str, approved: bool = True) -> bool:
        """
        Handle the approval or rejection of a response by a human.

        Args:
            comment_id: ID of the comment
            approved: Whether the response was approved

        Returns:
            True if the workflow was successfully resumed, False otherwise
        """
        try:
            logger.info(
                f"Handling response approval for comment {comment_id}: approved={approved}"
            )

            # Resume the workflow
            from .workflows.sentiment_workflow import resume_workflow_after_approval

            final_state = asyncio.run(
                resume_workflow_after_approval(comment_id, approved)
            )

            if not final_state:
                logger.error(f"Failed to resume workflow for comment {comment_id}")
                return False

            # Extract final_response and ensure it's a string
            final_response = final_state.get("final_response")
            if final_response is not None and hasattr(final_response, "content"):
                final_response = final_response.content

            # Update the comment in the database
            try:
                # Update the database using the final response
                self.db.update_comment_approval(
                    comment_id=comment_id,
                    approved=approved,
                    final_response=final_response if approved else None,
                )

                logger.info(
                    f"Updated comment {comment_id} in database: approved={approved}"
                )
            except Exception as db_error:
                logger.error(f"Error updating comment in database: {str(db_error)}")

            if final_state and approved:
                logger.info(f"Successfully resumed workflow for comment {comment_id}")

                # Get the final response from the workflow state
                if final_response:
                    # Post the response to Reddit
                    comment_data = self.db.get_comment(comment_id)
                    if comment_data:
                        try:
                            asyncio.run(
                                self.collector.post_response(
                                    comment_id=comment_data[
                                        "comment_id"
                                    ],  # Use Reddit comment ID
                                    response_text=final_response,
                                )
                            )
                            logger.info(
                                f"Posted approved response to comment {comment_id}"
                            )
                        except Exception as e:
                            logger.error(f"Error posting response to Reddit: {str(e)}")
                    else:
                        logger.error(f"Could not find comment {comment_id} in database")
                else:
                    logger.error(
                        f"No final response in workflow state for comment {comment_id}"
                    )
            else:
                logger.info(f"Workflow for comment {comment_id} marked as not approved")

            return True
        except Exception as e:
            logger.error(f"Error handling response approval: {str(e)}")
            return False
