#!/usr/bin/env python3
"""
Script to completely recreate the database by removing the existing one and creating a new one.
This ensures a completely fresh start with no existing comments or data.
"""

import logging
import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

import shutil
import sqlite3

from src.reddit_sentiment_analysis.storage.comment_db import CommentDatabase
from src.reddit_sentiment_analysis.workflows.sentiment_workflow import (
    WorkflowStateManager,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def recreate_database():
    """Completely recreate the database by removing the existing one."""
    try:
        # Initialize the database connection to get the path
        db = CommentDatabase()
        db_path = db.db_path

        logger.info(f"Database file location: {db_path}")

        # Close any existing connections and remove the file
        if os.path.exists(db_path):
            logger.info(f"Removing existing database file: {db_path}")
            try:
                # Make sure no connections are active
                os.remove(db_path)
                logger.info("Existing database file successfully removed")
            except Exception as e:
                logger.error(f"Error removing database file: {e}")
                logger.info("Trying alternative approach...")

                # If we can't remove the file directly, try to rename it
                backup_path = f"{db_path}.bak"
                try:
                    shutil.move(db_path, backup_path)
                    logger.info(f"Moved existing database to {backup_path}")
                except Exception as e2:
                    logger.error(f"Failed to rename database: {e2}")
                    return False
        else:
            logger.info("No existing database file found")

        # Clear workflow states
        workflow_manager = WorkflowStateManager()
        workflow_states_dir = workflow_manager.storage_dir

        if os.path.exists(workflow_states_dir):
            logger.info(f"Clearing workflow states from: {workflow_states_dir}")

            # Remove all workflow state files
            workflow_files = list(Path(workflow_states_dir).glob("*.json"))
            for file_path in workflow_files:
                try:
                    os.remove(file_path)
                    logger.info(f"Removed workflow state file: {file_path}")
                except Exception as e:
                    logger.error(f"Error removing workflow state file {file_path}: {e}")

        # Check for any other files in the data directory that may need clearing
        data_dir = Path(db_path).parent  # This should be the 'data' directory

        # Identify any monitoring state files and remove them
        monitor_files = list(data_dir.glob("monitor_*.json"))
        for file_path in monitor_files:
            try:
                os.remove(file_path)
                logger.info(f"Removed monitoring state file: {file_path}")
            except Exception as e:
                logger.error(f"Error removing monitoring state file {file_path}: {e}")

        # Create the data directory if it doesn't exist (it might have been removed)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Create the workflow states directory if it doesn't exist
        os.makedirs(workflow_states_dir, exist_ok=True)

        # Create a new database
        logger.info("Creating new database...")

        # Initialize the database again to create the new schema
        new_db = CommentDatabase()

        # Verify creation
        conn = sqlite3.connect(new_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM comments")
        count = cursor.fetchone()[0]
        conn.close()

        logger.info(f"New database created successfully with {count} comments")
        return True

    except Exception as e:
        logger.error(f"Error recreating database: {e}")
        return False


def clean_start():
    """Set up a completely fresh environment by clearing all persisted data."""
    # Recreate the database
    success = recreate_database()

    if not success:
        return False

    # Find and remove any lock files
    try:
        # App root directory
        app_dir = Path(__file__).parent.parent

        # Search for monitor lock files
        lock_files = list(app_dir.glob("**/monitor.lock"))
        for lock_file in lock_files:
            try:
                os.remove(lock_file)
                logger.info(f"Removed lock file: {lock_file}")
            except Exception as e:
                logger.error(f"Error removing lock file {lock_file}: {e}")

        return True
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return False


if __name__ == "__main__":
    print("This script will completely recreate your environment for a fresh start.")
    print(
        "All existing comments, workflow states, and monitoring data will be permanently lost."
    )
    print("Are you sure you want to proceed? (y/N): ", end="")

    confirmation = input().strip().lower()

    if confirmation == "y":
        success = clean_start()
        if success:
            print("\nFresh start successful! All data has been cleared.")
            print(
                "The application will start with a clean database when you run it next."
            )
        else:
            print("\nFailed to complete the fresh start. Check the logs for details.")
    else:
        print("Operation cancelled.")
