#!/usr/bin/env python3
"""
Script to verify that the database setup is correct.
This script checks:
1. The path to the primary database
2. That only necessary database files exist
3. That the database schema is correct
"""

import logging
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

# Import our custom modules
from src.reddit_sentiment_analysis.storage.comment_db import CommentDatabase

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
        return db_files
    except subprocess.CalledProcessError as e:
        logger.error(f"Error finding database files: {e}")
        # Fallback to manual search if find command fails
        db_files = list(project_dir.glob("**/*.db"))
        return db_files


def verify_database_schema(db_path):
    """Verify that the database has the correct schema."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check for comments table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='comments'"
        )
        has_table = cursor.fetchone() is not None

        if not has_table:
            print(f"❌ Database {db_path} does not have a 'comments' table")
            conn.close()
            return False

        # Check columns in the comments table
        cursor.execute("PRAGMA table_info(comments)")
        columns = [row[1] for row in cursor.fetchall()]

        expected_columns = [
            "id",
            "comment_id",
            "subreddit",
            "author",
            "body",
            "created_utc",
            "permalink",
            "key_term",
            "sentiment",
            "confidence",
            "ai_response",
            "status",
            "email_sent",
            "email_recipient",
            "timestamp",
        ]

        missing_columns = [col for col in expected_columns if col not in columns]
        extra_columns = [col for col in columns if col not in expected_columns]

        if missing_columns:
            print(
                f"❌ Database {db_path} is missing columns: {', '.join(missing_columns)}"
            )
            conn.close()
            return False

        if extra_columns:
            print(f"⚠️ Database {db_path} has extra columns: {', '.join(extra_columns)}")

        # Get comment count
        cursor.execute("SELECT COUNT(*) FROM comments")
        count = cursor.fetchone()[0]

        conn.close()
        return True, count
    except Exception as e:
        logger.error(f"Error verifying database schema for {db_path}: {e}")
        return False, 0


def verify_database_setup():
    """Verify that the database setup is correct."""
    print("Verifying database setup...")

    # Check which database the application uses
    db = CommentDatabase()
    primary_db_path = db.db_path
    print(f"Primary database used by application: {primary_db_path}")

    # Check if the primary database exists
    if not primary_db_path.exists():
        print(f"❌ Primary database file does not exist: {primary_db_path}")
        return False

    # Verify the primary database schema
    schema_ok, count = verify_database_schema(primary_db_path)
    if schema_ok:
        print(f"✅ Primary database schema is correct")
        print(f"📊 Primary database has {count} comments")
    else:
        print(f"❌ Primary database schema is incorrect")
        return False

    # Find all database files in the project
    all_db_files = find_all_database_files()
    print(f"Found {len(all_db_files)} database files:")

    # Expected database files (primary and test)
    script_dir = Path(__file__).parent.absolute()
    app_dir = script_dir.parent
    project_dir = app_dir.parent
    expected_db_files = [
        project_dir / "data" / "comments.db",  # Primary database
        app_dir / "data" / "test_comments.db",  # Test database
    ]

    # Check if there are any unexpected database files
    unexpected_db_files = []
    for db_file in all_db_files:
        is_expected = False
        for expected_path in expected_db_files:
            if (
                os.path.samefile(db_file, expected_path)
                if db_file.exists() and expected_path.exists()
                else str(db_file) == str(expected_path)
            ):
                is_expected = True
                break

        if is_expected:
            print(f"   ✅ {db_file} - Expected")
        else:
            print(f"   ❌ {db_file} - Unexpected")
            unexpected_db_files.append(db_file)

    # Warn if there are unexpected database files
    if unexpected_db_files:
        print(f"\n⚠️ Found {len(unexpected_db_files)} unexpected database files")
        print("To consolidate all databases, run:")
        print("   python app/scripts/consolidate_databases.py")
    else:
        print("\n✅ Database setup is correct")

    return len(unexpected_db_files) == 0


if __name__ == "__main__":
    verify_database_setup()
