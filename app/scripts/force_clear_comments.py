#!/usr/bin/env python3
"""
Script to forcefully clear all comments from the database and cached session state.
This creates direct SQL delete statements and attempts to clear any UI caches as well.
"""

import glob
import json
import logging
import os
import shutil
import sqlite3
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def find_db_files():
    """Find all database files in the project."""
    app_dir = Path(__file__).parent.parent
    project_dir = app_dir.parent

    # Look for SQLite database files
    db_files = []
    for ext in [".db", ".sqlite", ".sqlite3"]:
        db_files.extend(list(project_dir.glob(f"**/*{ext}")))

    return db_files


def force_clear_comments():
    """Forcefully clear all comments from all possible databases."""
    app_dir = Path(__file__).parent.parent
    project_dir = app_dir.parent
    data_dir = app_dir / "data"

    cleared_count = 0

    # 1. Find all database files
    db_files = find_db_files()
    logger.info(f"Found {len(db_files)} potential database files")

    # 2. Clear each database file we find
    for db_path in db_files:
        try:
            logger.info(f"Clearing database at {db_path}")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check if the 'comments' table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='comments'"
            )
            if cursor.fetchone():
                # Get count before deletion
                cursor.execute("SELECT COUNT(*) FROM comments")
                count_before = cursor.fetchone()[0]

                # Delete all comments
                cursor.execute("DELETE FROM comments")
                conn.commit()

                # Get count after deletion
                cursor.execute("SELECT COUNT(*) FROM comments")
                count_after = cursor.fetchone()[0]

                cleared_count += count_before
                logger.info(f"Cleared {count_before} comments from {db_path}")
            else:
                logger.info(f"No 'comments' table found in {db_path}")

            conn.close()
        except Exception as e:
            logger.error(f"Error clearing database {db_path}: {e}")

    # 3. Find and clear any Streamlit cache directories
    try:
        # Clear Streamlit cache directories
        st_cache_dirs = list(project_dir.glob("**/.streamlit/cache"))
        for cache_dir in st_cache_dirs:
            logger.info(f"Clearing Streamlit cache at {cache_dir}")
            try:
                shutil.rmtree(cache_dir)
                logger.info(f"Cleared Streamlit cache at {cache_dir}")
            except Exception as e:
                logger.error(f"Error clearing Streamlit cache at {cache_dir}: {e}")
    except Exception as e:
        logger.error(f"Error finding Streamlit cache: {e}")

    # 4. Clear workflow states
    workflow_states_dir = data_dir / "workflow_states"
    if workflow_states_dir.exists():
        try:
            # Remove all files in the workflow states directory
            for file_path in workflow_states_dir.glob("*.json"):
                os.remove(file_path)
                logger.info(f"Removed workflow state: {file_path}")
        except Exception as e:
            logger.error(f"Error clearing workflow states: {e}")

    # 5. Clear monitor state files
    try:
        monitor_files = list(project_dir.glob("**/monitor*.json"))
        monitor_files.extend(list(project_dir.glob("**/monitor.lock")))

        for file_path in monitor_files:
            try:
                os.remove(file_path)
                logger.info(f"Removed monitor state file: {file_path}")
            except Exception as e:
                logger.error(f"Error removing monitor file {file_path}: {e}")
    except Exception as e:
        logger.error(f"Error clearing monitor files: {e}")

    # 6. Clear any Streamlit session state file if it exists
    try:
        session_files = list(project_dir.glob("**/.streamlit/session_state*.json"))
        for file_path in session_files:
            try:
                os.remove(file_path)
                logger.info(f"Removed Streamlit session state: {file_path}")
            except Exception as e:
                logger.error(f"Error removing session state {file_path}: {e}")
    except Exception as e:
        logger.error(f"Error clearing session states: {e}")

    # 7. Create an empty database file as a last resort
    try:
        main_db_path = data_dir / "comments.db"
        if main_db_path.exists():
            # Create a new empty database
            os.remove(main_db_path)
            logger.info("Removed main database")

            # Create a new empty database
            conn = sqlite3.connect(main_db_path)
            cursor = conn.cursor()

            # Create the comments table schema
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
            logger.info("Created new empty database")
    except Exception as e:
        logger.error(f"Error creating new empty database: {e}")

    return cleared_count


if __name__ == "__main__":
    print("Forcefully clearing all comments from the application...")
    print("This will directly remove all comments from all databases and caches.")

    count = force_clear_comments()

    print(f"\nCleared {count} comments from the system.")
    print("Please restart the application for changes to take effect.")
    print("Note: You will need to close and re-open the application completely.")
