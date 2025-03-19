"""
Database for storing and retrieving Reddit comments.
"""

import json
import logging
import os
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CommentDatabase:
    """Database for storing and retrieving Reddit comments."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """
        Initialize the database.

        Args:
            db_path: Path to the SQLite database file
        """
        if db_path is None:
            # Get the project root directory
            current_file = Path(__file__).resolve()
            src_dir = (
                current_file.parent.parent.parent
            )  # src/reddit_sentiment_analysis/storage -> src
            app_dir = src_dir.parent  # src -> app
            project_dir = app_dir.parent  # app -> project root

            # Use the primary database at the project root
            db_path = project_dir / "data" / "comments.db"

            logger.info(f"Using primary database at: {db_path}")
        else:
            # If an explicit path is provided (for testing), use it as is
            db_path = Path(db_path)
            logger.info(f"Using custom database at: {db_path}")

        self.db_path = Path(db_path)

        # Create directory if it doesn't exist
        os.makedirs(self.db_path.parent, exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create comments table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS comments (
            id TEXT PRIMARY KEY,
            comment_id TEXT UNIQUE,
            subreddit TEXT,
            author TEXT,
            body TEXT,
            created_utc REAL,
            permalink TEXT,
            key_term TEXT,
            sentiment TEXT,
            confidence REAL,
            ai_response TEXT,
            status TEXT,
            email_sent INTEGER,
            email_recipient TEXT,
            timestamp REAL
        )
        """
        )

        conn.commit()
        conn.close()

        logger.info(f"Initialized database at {self.db_path}")

    def add_comment(
        self,
        comment_data: Dict,
        key_term: str,
        sentiment: str,
        confidence: float,
        ai_response: Optional[str] = None,
        status: str = "new",
        email_sent: bool = False,
        email_recipient: Optional[str] = None,
    ) -> str:
        """
        Add a comment to the database.

        Args:
            comment_data: Dictionary containing comment data
            key_term: The key term that triggered this comment
            sentiment: Sentiment analysis result
            confidence: Confidence score for sentiment
            ai_response: AI-generated response (if any)
            status: Status of the comment (new, pending_approval, approved, rejected)
            email_sent: Whether an email alert has been sent
            email_recipient: Email address that received the alert

        Returns:
            ID of the added comment
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Generate a unique ID
        comment_id = comment_data.get("id")
        id = str(uuid.uuid4())

        # Log the comment data for debugging
        logger.info(f"Adding comment to database with Reddit ID: {comment_id}")
        logger.debug(f"Comment data: {json.dumps(comment_data, default=str)}")

        try:
            cursor.execute(
                """
                INSERT INTO comments (
                    id, comment_id, subreddit, author, body, created_utc, permalink,
                    key_term, sentiment, confidence, ai_response, status,
                    email_sent, email_recipient, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id,
                    comment_id,
                    comment_data.get("subreddit", ""),
                    comment_data.get("author", ""),
                    comment_data.get("body", ""),
                    comment_data.get("created_utc", 0),
                    comment_data.get("permalink", ""),
                    key_term,
                    sentiment,
                    confidence,
                    ai_response,
                    status,
                    1 if email_sent else 0,
                    email_recipient,
                    time.time(),
                ),
            )

            conn.commit()
            logger.info(f"Added comment {id} to database with Reddit ID: {comment_id}")

        except sqlite3.IntegrityError:
            # Comment already exists, update instead
            logger.info(f"Comment {comment_id} already exists, updating")
            cursor.execute(
                """
                UPDATE comments SET
                    subreddit = ?,
                    author = ?,
                    body = ?,
                    created_utc = ?,
                    permalink = ?,
                    key_term = ?,
                    sentiment = ?,
                    confidence = ?,
                    ai_response = ?,
                    status = ?,
                    email_sent = ?,
                    email_recipient = ?,
                    timestamp = ?
                WHERE comment_id = ?
                """,
                (
                    comment_data.get("subreddit", ""),
                    comment_data.get("author", ""),
                    comment_data.get("body", ""),
                    comment_data.get("created_utc", 0),
                    comment_data.get("permalink", ""),
                    key_term,
                    sentiment,
                    confidence,
                    ai_response,
                    status,
                    1 if email_sent else 0,
                    email_recipient,
                    time.time(),
                    comment_id,
                ),
            )

            # Get the ID of the updated comment
            cursor.execute(
                "SELECT id FROM comments WHERE comment_id = ?", (comment_id,)
            )
            result = cursor.fetchone()
            if result:
                id = result[0]

            conn.commit()

        conn.close()
        return id

    def update_comment_status(self, comment_id: str, status: str) -> bool:
        """
        Update the status of a comment.

        Args:
            comment_id: ID of the comment to update
            status: New status

        Returns:
            True if the comment was updated, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE comments SET status = ? WHERE id = ?", (status, comment_id)
        )

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if updated:
            logger.info(f"Updated comment {comment_id} status to {status}")

        return updated

    def update_comment_approval(
        self, comment_id: str, approved: bool, final_response: Optional[str] = None
    ) -> bool:
        """
        Update the approval status of a comment and mark it for workflow resumption.

        Args:
            comment_id: ID of the comment to update
            approved: Whether the response was approved by a human
            final_response: Final approved response (if provided)

        Returns:
            True if the comment was updated, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Update status based on approval
        status = "approved" if approved else "rejected"

        # If approved, also set final_response
        if approved:
            # If final_response is provided, use it; otherwise get the AI response
            response_to_use = final_response
            if not response_to_use:
                # Get the AI response
                cursor.execute(
                    "SELECT ai_response FROM comments WHERE id = ?", (comment_id,)
                )
                row = cursor.fetchone()
                if row and row["ai_response"]:
                    response_to_use = row["ai_response"]

            if response_to_use:
                # Set status, human_approved, and final_response
                cursor.execute(
                    "UPDATE comments SET status = ?, human_approved = ?, final_response = ? WHERE id = ?",
                    (status, 1 if approved else 0, response_to_use, comment_id),
                )
            else:
                # No response available, just update status and human_approved
                cursor.execute(
                    "UPDATE comments SET status = ?, human_approved = ? WHERE id = ?",
                    (status, 1 if approved else 0, comment_id),
                )
        else:
            # Not approved, just update status and human_approved
            cursor.execute(
                "UPDATE comments SET status = ?, human_approved = ? WHERE id = ?",
                (status, 0, comment_id),
            )

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if updated:
            logger.info(f"Updated comment {comment_id} approval status to {approved}")

        return updated

    def update_ai_response(self, comment_id: str, ai_response: str) -> bool:
        """
        Update the AI response for a comment.

        Args:
            comment_id: ID of the comment to update
            ai_response: New AI response

        Returns:
            True if the comment was updated, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE comments SET ai_response = ? WHERE id = ?",
            (ai_response, comment_id),
        )

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if updated:
            logger.info(f"Updated AI response for comment {comment_id}")

        return updated

    def mark_email_sent(self, comment_id: str, email_recipient: str) -> bool:
        """
        Mark a comment as having an email sent.

        Args:
            comment_id: ID of the comment
            email_recipient: Email address that received the alert

        Returns:
            True if the comment was updated, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE comments SET email_sent = 1, email_recipient = ? WHERE id = ?",
            (email_recipient, comment_id),
        )

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if updated:
            logger.info(
                f"Marked email sent for comment {comment_id} to {email_recipient}"
            )

        return updated

    def get_comment(self, comment_id: str) -> Optional[Dict]:
        """
        Get a comment by ID.

        Args:
            comment_id: ID of the comment

        Returns:
            Comment data or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM comments WHERE id = ?", (comment_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            return dict(row)

        return None

    def get_comment_by_reddit_id(self, reddit_comment_id: str) -> Optional[Dict]:
        """
        Get a comment by Reddit comment ID.

        Args:
            reddit_comment_id: Reddit comment ID

        Returns:
            Comment data or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Log the Reddit comment ID we're looking for
        logger.info(f"Looking for comment with Reddit ID: {reddit_comment_id}")

        # Try with and without t1_ prefix
        if reddit_comment_id.startswith("t1_"):
            # Try with the prefix
            cursor.execute(
                "SELECT * FROM comments WHERE comment_id = ?", (reddit_comment_id,)
            )
            row = cursor.fetchone()

            # If not found, try without the prefix
            if not row:
                stripped_id = reddit_comment_id[3:]  # Remove t1_
                cursor.execute(
                    "SELECT * FROM comments WHERE comment_id = ?", (stripped_id,)
                )
                row = cursor.fetchone()
        else:
            # Try without the prefix
            cursor.execute(
                "SELECT * FROM comments WHERE comment_id = ?", (reddit_comment_id,)
            )
            row = cursor.fetchone()

            # If not found, try with the prefix
            if not row:
                prefixed_id = f"t1_{reddit_comment_id}"
                cursor.execute(
                    "SELECT * FROM comments WHERE comment_id = ?", (prefixed_id,)
                )
                row = cursor.fetchone()

        conn.close()

        if row:
            logger.info(f"Found comment with Reddit ID: {reddit_comment_id}")
            return dict(row)
        else:
            logger.warning(f"No comment found with Reddit ID: {reddit_comment_id}")
            return None

    def get_all_comments(self, limit: int = 500) -> List[Dict]:
        """
        Get all comments.

        Args:
            limit: Maximum number of comments to return (default: 500)

        Returns:
            List of comment data
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Log the query for debugging
        logger.info(f"Fetching up to {limit} comments from database")

        cursor.execute(
            "SELECT * FROM comments ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        rows = cursor.fetchall()

        comment_count = len(rows)
        logger.info(f"Retrieved {comment_count} comments from database")

        conn.close()

        return [dict(row) for row in rows]

    def get_comments_by_sentiment(self, sentiment: str, limit: int = 500) -> List[Dict]:
        """
        Get comments by sentiment.

        Args:
            sentiment: Sentiment to filter by
            limit: Maximum number of comments to return (default: 500)

        Returns:
            List of comment data
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        logger.info(f"Fetching up to {limit} comments with sentiment '{sentiment}'")

        cursor.execute(
            "SELECT * FROM comments WHERE sentiment = ? ORDER BY timestamp DESC LIMIT ?",
            (sentiment, limit),
        )
        rows = cursor.fetchall()

        comment_count = len(rows)
        logger.info(f"Retrieved {comment_count} comments with sentiment '{sentiment}'")

        conn.close()

        return [dict(row) for row in rows]

    def get_comments_by_status(self, status: str, limit: int = 500) -> List[Dict]:
        """
        Get comments by status.

        Args:
            status: Status to filter by
            limit: Maximum number of comments to return (default: 500)

        Returns:
            List of comment data
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        logger.info(f"Fetching up to {limit} comments with status '{status}'")

        cursor.execute(
            "SELECT * FROM comments WHERE status = ? ORDER BY timestamp DESC LIMIT ?",
            (status, limit),
        )
        rows = cursor.fetchall()

        comment_count = len(rows)
        logger.info(f"Retrieved {comment_count} comments with status '{status}'")

        conn.close()

        return [dict(row) for row in rows]

    def get_comments_by_key_term(self, key_term: str, limit: int = 100) -> List[Dict]:
        """
        Get comments by key term.

        Args:
            key_term: Key term to filter by
            limit: Maximum number of comments to return

        Returns:
            List of comment data
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM comments WHERE key_term = ? ORDER BY timestamp DESC LIMIT ?",
            (key_term, limit),
        )
        rows = cursor.fetchall()

        conn.close()

        return [dict(row) for row in rows]

    def get_recent_comments(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """
        Get recent comments.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of comments to return

        Returns:
            List of comment data
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Calculate cutoff time
        cutoff_time = time.time() - (hours * 3600)

        cursor.execute(
            "SELECT * FROM comments WHERE timestamp > ? ORDER BY timestamp DESC LIMIT ?",
            (cutoff_time, limit),
        )
        rows = cursor.fetchall()

        conn.close()

        return [dict(row) for row in rows]

    def comment_exists(self, reddit_comment_id: str) -> bool:
        """
        Check if a comment exists in the database.

        Args:
            reddit_comment_id: Reddit comment ID

        Returns:
            True if the comment exists, False otherwise
        """
        if not reddit_comment_id:
            logger.warning("Empty comment ID provided to comment_exists check")
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Log original input
        logger.info(f"Checking if comment exists - Input ID: '{reddit_comment_id}'")

        # Normalize the comment ID by ensuring we check both with and without t1_ prefix
        prefixed_id = reddit_comment_id
        stripped_id = reddit_comment_id

        if reddit_comment_id.startswith("t1_"):
            stripped_id = reddit_comment_id[3:]  # Remove t1_
        else:
            prefixed_id = f"t1_{reddit_comment_id}"  # Add t1_

        # Log all versions we're checking
        logger.info(
            f"Checking variants - Original: '{reddit_comment_id}', Prefixed: '{prefixed_id}', Stripped: '{stripped_id}'"
        )

        # First try exact match on comment_id field
        cursor.execute(
            "SELECT id, comment_id FROM comments WHERE comment_id = ?",
            (reddit_comment_id,),
        )
        result = cursor.fetchone()

        # For debugging, show the result
        if result:
            logger.info(
                f"Found exact match for '{reddit_comment_id}' - DB entry: {result}"
            )
            conn.close()
            return True

        # If not found, try with the prefixed version
        if reddit_comment_id != prefixed_id:
            cursor.execute(
                "SELECT id, comment_id FROM comments WHERE comment_id = ?",
                (prefixed_id,),
            )
            result = cursor.fetchone()
            if result:
                logger.info(
                    f"Found prefixed match for '{reddit_comment_id}' - DB entry: {result}"
                )
                conn.close()
                return True

        # If still not found, try with the stripped version
        if reddit_comment_id != stripped_id:
            cursor.execute(
                "SELECT id, comment_id FROM comments WHERE comment_id = ?",
                (stripped_id,),
            )
            result = cursor.fetchone()
            if result:
                logger.info(
                    f"Found stripped match for '{reddit_comment_id}' - DB entry: {result}"
                )
                conn.close()
                return True

        # Additional check - try a LIKE query to catch any other format variations
        cursor.execute(
            "SELECT id, comment_id FROM comments WHERE comment_id LIKE ?",
            (f"%{stripped_id}%",),
        )
        result = cursor.fetchone()
        if result:
            logger.info(
                f"Found partial match for '{reddit_comment_id}' - DB entry: {result}"
            )
            conn.close()
            return True

        # Log that no match was found
        cursor.execute(
            "SELECT comment_id FROM comments ORDER BY timestamp DESC LIMIT 5"
        )
        recent_comments = cursor.fetchall()
        recent_ids = [c[0] for c in recent_comments]
        logger.info(
            f"No match found for '{reddit_comment_id}'. Recent comment IDs in DB: {recent_ids}"
        )

        conn.close()
        return False
