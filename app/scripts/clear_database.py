#!/usr/bin/env python3
"""
Script to clear all comments from the database.
"""

import logging
import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

import sqlite3

from src.reddit_sentiment_analysis.storage.comment_db import CommentDatabase

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def clear_database():
    """Clear all comments from the database."""
    try:
        # Initialize the database
        db = CommentDatabase()

        # Connect to database
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # Count comments before deletion
        cursor.execute("SELECT COUNT(*) FROM comments")
        count_before = cursor.fetchone()[0]
        logger.info(f"Found {count_before} comments in the database")

        # Delete all comments
        cursor.execute("DELETE FROM comments")
        conn.commit()

        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM comments")
        count_after = cursor.fetchone()[0]

        conn.close()

        logger.info(f"Successfully deleted {count_before} comments from the database")
        logger.info(f"Remaining comments: {count_after}")

        return count_before

    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        return 0


if __name__ == "__main__":
    print("This script will delete ALL comments from the database.")
    print("Are you sure you want to proceed? (y/N): ", end="")

    confirmation = input().strip().lower()

    if confirmation == "y":
        count = clear_database()
        print(f"Successfully deleted {count} comments from the database.")
    else:
        print("Operation cancelled.")
