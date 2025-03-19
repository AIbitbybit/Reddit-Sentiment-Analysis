#!/usr/bin/env python
"""
Cleanup Script for Reddit Sentiment Analysis

This script helps clean up data and log files that accumulate over time.
It provides options to:
- Archive and compress old log files
- Backup and clean the SQLite database
- Remove temporary files
- Clear vector databases

Usage:
    python scripts/cleanup.py [options]

Options:
    --logs            Clean and archive log files
    --database        Backup and optimize the SQLite database
    --vector-db       Clear vector database
    --all             Perform all cleanup operations
    --dry-run         Show what would be done without making changes
    --days DAYS       Consider files older than DAYS days (default: 30)
    --backup-dir DIR  Directory to store backups (default: ./backups)
"""

import argparse
import datetime
import os
import shutil
import sqlite3
import sys
import tarfile
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


def setup_args():
    """Set up command-line arguments."""
    parser = argparse.ArgumentParser(description="Clean up data and log files")
    parser.add_argument("--logs", action="store_true", help="Clean log files")
    parser.add_argument("--database", action="store_true", help="Optimize database")
    parser.add_argument(
        "--vector-db", action="store_true", help="Clear vector database"
    )
    parser.add_argument(
        "--all", action="store_true", help="Perform all cleanup operations"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--days", type=int, default=30, help="Process files older than this many days"
    )
    parser.add_argument(
        "--backup-dir", type=str, default="./backups", help="Directory for backups"
    )

    return parser.parse_args()


def ensure_dir(directory):
    """Ensure a directory exists, creating it if necessary."""
    if not os.path.exists(directory):
        if not args.dry_run:
            os.makedirs(directory)
        print(f"Created directory: {directory}")


def clean_logs(args):
    """Archive and compress log files older than the specified number of days."""
    print("\n=== Cleaning Log Files ===")
    log_dir = project_root / "logs"
    backup_dir = project_root / args.backup_dir / "logs"

    if not os.path.exists(log_dir):
        print(f"Log directory {log_dir} not found, skipping...")
        return

    ensure_dir(backup_dir)

    # Get current timestamp for archive name
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"logs_archive_{timestamp}.tar.gz"
    archive_path = backup_dir / archive_name

    # Find old log files
    cutoff_time = time.time() - (args.days * 24 * 3600)
    old_logs = []

    for file in os.listdir(log_dir):
        file_path = os.path.join(log_dir, file)
        if os.path.isfile(file_path) and file.endswith(".txt") or file.endswith(".log"):
            mod_time = os.path.getmtime(file_path)
            if mod_time < cutoff_time:
                old_logs.append(file_path)
                print(f"Found old log file: {file}")

    if not old_logs:
        print(f"No log files older than {args.days} days found.")
        return

    # Create archive
    if not args.dry_run:
        with tarfile.open(archive_path, "w:gz") as tar:
            for log_file in old_logs:
                tar.add(log_file, arcname=os.path.basename(log_file))

        # Remove archived log files
        for log_file in old_logs:
            os.remove(log_file)

        print(f"Archived {len(old_logs)} log files to {archive_path}")
        print(f"Removed {len(old_logs)} old log files")
    else:
        print(f"Would archive {len(old_logs)} log files to {archive_path}")
        print(f"Would remove {len(old_logs)} old log files")


def optimize_database(args):
    """Backup and optimize the SQLite database."""
    print("\n=== Optimizing Database ===")
    db_path = project_root / "data" / "comments.db"
    backup_dir = project_root / args.backup_dir / "database"

    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found, skipping...")
        return

    ensure_dir(backup_dir)

    # Get current timestamp for backup name
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"comments_db_backup_{timestamp}.sqlite"
    backup_path = backup_dir / backup_name

    # Backup database
    if not args.dry_run:
        shutil.copy2(db_path, backup_path)
        print(f"Backed up database to {backup_path}")

        # Optimize database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("VACUUM")
        cursor.execute("ANALYZE")
        conn.commit()
        conn.close()
        print("Optimized database")
    else:
        print(f"Would back up database to {backup_path}")
        print("Would optimize database")


def clear_vector_db(args):
    """Clear vector database files."""
    print("\n=== Clearing Vector Database ===")
    vector_db_dir = project_root / "data" / "vector_db"
    backup_dir = project_root / args.backup_dir / "vector_db"

    if not os.path.exists(vector_db_dir):
        print(f"Vector database directory {vector_db_dir} not found, skipping...")
        return

    ensure_dir(backup_dir)

    # Get current timestamp for backup name
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"vector_db_backup_{timestamp}"
    backup_path = backup_dir / backup_name

    # Count files
    file_count = sum(1 for _ in Path(vector_db_dir).glob("**/*") if _.is_file())

    if file_count == 0:
        print("No vector database files found.")
        return

    # Backup and clear
    if not args.dry_run:
        shutil.copytree(vector_db_dir, backup_path)
        print(f"Backed up vector database to {backup_path}")

        # Clear files but keep directory structure
        for item in os.listdir(vector_db_dir):
            item_path = os.path.join(vector_db_dir, item)
            if os.path.isfile(item_path) and not item == ".keep":
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                os.makedirs(item_path)
                # Create .keep file
                with open(os.path.join(item_path, ".keep"), "w") as f:
                    pass

        print(f"Cleared vector database ({file_count} files)")
    else:
        print(f"Would back up vector database to {backup_path}")
        print(f"Would clear vector database ({file_count} files)")


if __name__ == "__main__":
    args = setup_args()

    # Show what will be done
    print(f"Cleanup operations with {'DRY RUN - ' if args.dry_run else ''}settings:")
    print(f"- Looking for files older than {args.days} days")
    print(f"- Backup directory: {args.backup_dir}")

    # Create main backup directory
    ensure_dir(project_root / args.backup_dir)

    # Perform requested operations
    if args.all or args.logs:
        clean_logs(args)

    if args.all or args.database:
        optimize_database(args)

    if args.all or args.vector_db:
        clear_vector_db(args)

    if not (args.logs or args.database or args.vector_db or args.all):
        print(
            "\nNo cleanup operations selected. Use --logs, --database, --vector-db, or --all."
        )
        print("For more information, use --help")

    print("\nCleanup completed.")
