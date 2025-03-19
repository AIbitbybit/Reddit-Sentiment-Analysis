#!/usr/bin/env python
"""
Database setup script for Reddit Sentiment Analysis.
This script creates the necessary tables in the SQLite database.
"""

import logging
import os
import sqlite3
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_db_path():
    """Get the path to the SQLite database file."""
    # Get the directory where the script is located
    script_dir = Path(__file__).parent.absolute()

    # Create a data directory if it doesn't exist
    data_dir = script_dir / "data"
    data_dir.mkdir(exist_ok=True)

    # Return the path to the database file
    return data_dir / "comments.db"


def setup_database():
    """Set up the SQLite database with the necessary tables."""
    db_path = get_db_path()

    logger.info(f"Setting up database at {db_path}")

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the comments table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS comments (
        id TEXT PRIMARY KEY,
        subreddit TEXT NOT NULL,
        author TEXT NOT NULL,
        body TEXT NOT NULL,
        created_utc REAL NOT NULL,
        permalink TEXT NOT NULL,
        key_term TEXT NOT NULL,
        sentiment TEXT NOT NULL,
        confidence REAL NOT NULL,
        ai_response TEXT,
        response_status TEXT DEFAULT 'pending',
        email_sent INTEGER DEFAULT 0,
        email_confirmed INTEGER DEFAULT 0,
        response_posted INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    # Create the email_confirmations table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS email_confirmations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        comment_id TEXT NOT NULL,
        confirmation_code TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY (comment_id) REFERENCES comments (id)
    )
    """
    )

    # Create indices for faster queries
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_comments_key_term ON comments (key_term)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_comments_sentiment ON comments (sentiment)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_comments_response_status ON comments (response_status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_comments_email_confirmed ON comments (email_confirmed)"
    )

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    logger.info("Database setup complete")
    return db_path


def main():
    """Main function to set up the database."""
    try:
        db_path = setup_database()
        print(f"Database successfully set up at: {db_path}")
        print("You can now run the Reddit Sentiment Analysis application.")
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        print(f"Error setting up database: {e}")
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
