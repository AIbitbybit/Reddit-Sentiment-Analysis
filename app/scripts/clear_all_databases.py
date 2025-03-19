#!/usr/bin/env python3
"""
Script to clear ALL database files found in the project.
This script will find and reset all SQLite database files to ensure a completely fresh start.
"""

import logging
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def find_all_database_files():
    """Find all SQLite database files in the project."""
    # Get the project root directory
    script_dir = Path(__file__).parent.absolute()
    app_dir = script_dir.parent
    project_dir = app_dir.parent

    logger.info(f"Searching for database files in: {project_dir}")

    # Use find command to locate all .db files
    try:
        result = subprocess.run(
            ["find", str(project_dir), "-name", "*.db"],
            capture_output=True,
            text=True,
            check=True,
        )
        db_files = [
            Path(line.strip()) for line in result.stdout.splitlines() if line.strip()
        ]
        logger.info(f"Found {len(db_files)} database files: {db_files}")
        return db_files
    except subprocess.CalledProcessError as e:
        logger.error(f"Error finding database files: {e}")
        # Fallback to manual search if find command fails
        db_files = list(project_dir.glob("**/*.db"))
        logger.info(f"Fallback search found {len(db_files)} database files")
        return db_files


def reset_database(db_path):
    """Reset a database file by removing all data from the comments table."""
    logger.info(f"Resetting database: {db_path}")

    try:
        # Check if the file exists
        if not os.path.exists(db_path):
            logger.warning(f"Database file not found: {db_path}")
            return False

        # Create a backup of the database
        backup_path = f"{db_path}.bak"
        try:
            shutil.copy2(db_path, backup_path)
            logger.info(f"Created backup at: {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")

        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if the comments table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='comments'"
        )
        if cursor.fetchone():
            # Get count before deletion
            cursor.execute("SELECT COUNT(*) FROM comments")
            count_before = cursor.fetchone()[0]
            logger.info(f"Found {count_before} comments")

            # Delete all comments
            cursor.execute("DELETE FROM comments")
            conn.commit()

            # Verify deletion
            cursor.execute("SELECT COUNT(*) FROM comments")
            count_after = cursor.fetchone()[0]

            logger.info(
                f"Removed {count_before - count_after} comments, remaining: {count_after}"
            )

            # Vacuum the database to reclaim space and optimize
            cursor.execute("VACUUM")
            conn.commit()

            conn.close()
            return True
        else:
            logger.warning(f"No 'comments' table found in {db_path}")
            conn.close()
            return False
    except Exception as e:
        logger.error(f"Error resetting database {db_path}: {e}")
        return False


def clear_streamlit_cache():
    """Clear any Streamlit cache directories."""
    script_dir = Path(__file__).parent.absolute()
    app_dir = script_dir.parent
    project_dir = app_dir.parent

    try:
        # Find all .streamlit directories
        streamlit_dirs = list(project_dir.glob("**/.streamlit"))
        logger.info(f"Found {len(streamlit_dirs)} Streamlit directories")

        for st_dir in streamlit_dirs:
            cache_dir = st_dir / "cache"
            if cache_dir.exists():
                logger.info(f"Clearing Streamlit cache: {cache_dir}")
                try:
                    shutil.rmtree(cache_dir)
                    logger.info(f"Successfully cleared cache: {cache_dir}")
                except Exception as e:
                    logger.error(f"Error clearing cache directory {cache_dir}: {e}")

            # Also clear any session state files
            for state_file in st_dir.glob("session_state*.json"):
                try:
                    os.remove(state_file)
                    logger.info(f"Removed session state file: {state_file}")
                except Exception as e:
                    logger.error(f"Error removing session state file {state_file}: {e}")
    except Exception as e:
        logger.error(f"Error clearing Streamlit cache: {e}")


def main():
    """Find and reset all database files in the project."""
    print("Starting comprehensive database reset...")

    # First, clear any Streamlit cache directories
    clear_streamlit_cache()

    # Find all database files
    db_files = find_all_database_files()

    # Keep track of success/failure
    success_count = 0
    failure_count = 0
    total_comments_cleared = 0

    # Reset each database
    for db_path in db_files:
        try:
            # Connect to count comments before deletion
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check if the comments table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='comments'"
            )
            if cursor.fetchone():
                # Get count before deletion
                cursor.execute("SELECT COUNT(*) FROM comments")
                count_before = cursor.fetchone()[0]
                total_comments_cleared += count_before
                conn.close()

                # Reset the database
                if reset_database(db_path):
                    success_count += 1
                    print(f"✓ Cleared {count_before} comments from {db_path}")
                else:
                    failure_count += 1
                    print(f"✗ Failed to reset {db_path}")
            else:
                print(f"- No comments table in {db_path}")
                conn.close()
        except Exception as e:
            logger.error(f"Error processing {db_path}: {e}")
            failure_count += 1
            print(f"✗ Error with {db_path}: {str(e)}")

    print("\nReset Summary:")
    print(f"- Found {len(db_files)} database files")
    print(f"- Successfully reset {success_count} databases")
    print(f"- Failed to reset {failure_count} databases")
    print(f"- Cleared approximately {total_comments_cleared} comments in total")

    print(
        "\nIMPORTANT: Please completely restart your application for changes to take effect."
    )
    print(
        "IMPORTANT: You must close and re-open the application, not just refresh the page."
    )


if __name__ == "__main__":
    main()
