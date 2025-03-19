#!/usr/bin/env python3
"""
Script to consolidate all databases into a single primary database.
This script will:
1. Identify all database files in the project
2. Determine which is the primary database
3. Copy all comments from other databases to the primary one
4. Remove unnecessary database files
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


def get_primary_database_path():
    """Determine the primary database path based on the application configuration."""
    # The primary database should be in the 'data' directory at the project root
    script_dir = Path(__file__).parent.absolute()
    app_dir = script_dir.parent
    project_dir = app_dir.parent

    primary_db_path = project_dir / "data" / "comments.db"

    # Create directory if it doesn't exist
    os.makedirs(primary_db_path.parent, exist_ok=True)

    # If the primary database doesn't exist yet, create it with the schema
    if not primary_db_path.exists():
        create_database_schema(primary_db_path)

    return primary_db_path


def create_database_schema(db_path):
    """Create a new database with the correct schema."""
    logger.info(f"Creating new database with schema: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create comments table schema
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

    logger.info(f"Created new database with schema: {db_path}")


def has_comments_table(db_path):
    """Check if a database has a comments table."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='comments'"
        )
        has_table = cursor.fetchone() is not None
        conn.close()
        return has_table
    except Exception as e:
        logger.error(f"Error checking for comments table in {db_path}: {e}")
        return False


def get_comment_count(db_path):
    """Get the number of comments in a database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM comments")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Error getting comment count from {db_path}: {e}")
        return 0


def copy_comments_to_primary(source_db, target_db):
    """Copy all comments from the source database to the primary database."""
    logger.info(f"Copying comments from {source_db} to {target_db}")

    try:
        # Connect to source database
        source_conn = sqlite3.connect(source_db)
        source_conn.row_factory = sqlite3.Row
        source_cursor = source_conn.cursor()

        # Connect to target database
        target_conn = sqlite3.connect(target_db)
        target_cursor = target_conn.cursor()

        # Get all comments from source
        source_cursor.execute("SELECT * FROM comments")
        comments = source_cursor.fetchall()
        comment_count = len(comments)

        if comment_count == 0:
            logger.info(f"No comments to copy from {source_db}")
            source_conn.close()
            target_conn.close()
            return 0

        # Insert comments into target, ignoring duplicates
        copied_count = 0
        for comment in comments:
            # Convert row to dict
            comment_dict = dict(comment)

            # Create placeholders and values for SQL
            placeholders = ", ".join(["?"] * len(comment_dict))
            columns = ", ".join(comment_dict.keys())
            values = tuple(comment_dict.values())

            try:
                # Use INSERT OR IGNORE to skip duplicates
                target_cursor.execute(
                    f"INSERT OR IGNORE INTO comments ({columns}) VALUES ({placeholders})",
                    values,
                )
                if target_cursor.rowcount > 0:
                    copied_count += 1
            except Exception as e:
                logger.error(
                    f"Error copying comment from {source_db} to {target_db}: {e}"
                )

        target_conn.commit()
        source_conn.close()
        target_conn.close()

        logger.info(
            f"Copied {copied_count} of {comment_count} comments from {source_db} to {target_db}"
        )
        return copied_count
    except Exception as e:
        logger.error(f"Error copying comments from {source_db} to {target_db}: {e}")
        return 0


def consolidate_databases():
    """Consolidate all databases into a single primary database."""
    # Find all databases
    db_files = find_all_database_files()

    # Get the primary database path
    primary_db = get_primary_database_path()
    logger.info(f"Primary database identified as: {primary_db}")

    # Verify primary database has the correct schema
    if not has_comments_table(primary_db):
        create_database_schema(primary_db)

    print(f"Primary database: {primary_db}")
    print(f"Found {len(db_files)} total database files")

    # Databases to keep (only the primary and test databases)
    keep_dbs = [primary_db]
    test_db = primary_db.parent / "test_comments.db"
    if test_db.exists():
        keep_dbs.append(test_db)

    # Process all databases
    copied_comments = 0
    removed_dbs = 0
    skipped_dbs = 0

    for db_path in db_files:
        # Skip the primary database (we don't need to copy from it)
        if db_path == primary_db:
            logger.info(f"Skipping primary database: {db_path}")
            continue

        # Skip test database (we want to keep this separate)
        if "test_comments.db" in str(db_path):
            logger.info(f"Skipping test database: {db_path}")
            skipped_dbs += 1
            continue

        # Check if the database has a comments table
        if not has_comments_table(db_path):
            logger.info(f"Skipping database without comments table: {db_path}")
            skipped_dbs += 1
            continue

        # Get comment count before copy
        comment_count = get_comment_count(db_path)
        if comment_count > 0:
            # Create a backup of the database before removing
            backup_path = f"{db_path}.bak"
            try:
                shutil.copy2(db_path, backup_path)
                logger.info(f"Created backup at: {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to create backup for {db_path}: {e}")

            # Copy comments to primary database
            copied = copy_comments_to_primary(db_path, primary_db)
            copied_comments += copied

        # Remove the database
        try:
            os.remove(db_path)
            logger.info(f"Removed database: {db_path}")
            removed_dbs += 1
        except Exception as e:
            logger.error(f"Failed to remove database {db_path}: {e}")

    # Print summary
    print("\nConsolidation Summary:")
    print(f"- Primary database: {primary_db}")
    print(f"- Comments copied to primary: {copied_comments}")
    print(f"- Databases removed: {removed_dbs}")
    print(f"- Databases kept: {len(db_files) - removed_dbs}")
    print(f"- Skipped databases: {skipped_dbs}\n")

    # Verify primary database
    primary_count = get_comment_count(primary_db)
    print(f"Primary database now contains {primary_count} comments")

    print("\nIMPORTANT: Please restart your application for changes to take effect.")

    return primary_count


if __name__ == "__main__":
    print("Starting database consolidation...\n")
    consolidate_databases()
