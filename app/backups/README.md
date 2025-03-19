# Backups Directory

This directory contains backups created by the cleanup script. These backups are stored in a structured format to help with recovery if needed.

## Directory Structure

- `logs/`: Contains archived log files
- `database/`: Contains SQLite database backups
- `vector_db/`: Contains vector database backups

## Backup Naming Convention

All backups include a timestamp in the format `YYYYMMDD_HHMMSS` to indicate when the backup was created:

- Log archives: `logs_archive_YYYYMMDD_HHMMSS.tar.gz`
- Database backups: `comments_db_backup_YYYYMMDD_HHMMSS.sqlite`
- Vector DB backups: `vector_db_backup_YYYYMMDD_HHMMSS/`

## Maintenance

This directory can grow large over time. Consider periodically moving older backups to external storage or deleting them if they are no longer needed.

## Recovery

To restore from a backup:

### Log Files

Log archives are mostly for historical purposes and typically don't need to be restored.

### Database

To restore a database backup:

1. Stop the application
2. Copy the backup file to the main data directory:
   ```
   cp backups/database/comments_db_backup_YYYYMMDD_HHMMSS.sqlite data/comments.db
   ```
3. Restart the application

### Vector Database

To restore a vector database:

1. Stop the application
2. Delete the current vector_db directory contents:
   ```
   rm -rf data/vector_db/*
   ```
3. Copy the backup contents:
   ```
   cp -r backups/vector_db/vector_db_backup_YYYYMMDD_HHMMSS/* data/vector_db/
   ```
4. Restart the application

## Automated Backups

The cleanup script automatically creates backups before performing any cleanup operations. To create backups manually, use:

```
python scripts/cleanup.py --all --dry-run
```

This will create backups without removing any files.
