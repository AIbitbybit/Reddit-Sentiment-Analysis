# Removed Modules

This directory contains modules that were removed from the main codebase but preserved for reference.

## Dashboard Module

**Removed:** March 2024

**Location:** `removed_modules/dashboard/`

**Reason for removal:**
The dashboard module was a separate visualization component that was superseded by the integrated History tab in the main application GUI. The functionality for viewing historical data and trends has been consolidated into the main application, making this standalone dashboard redundant.

**Original functionality:**

- Visualized sentiment trends over time
- Provided aspect-based sentiment breakdowns
- Offered subreddit comparison tools

**Entry point (removed):**

```python
# From pyproject.toml
reddit-dashboard = "reddit_sentiment_analysis.dashboard.app:run_gui"
```

**Usage in code (removed):**

```python
# From interactive.py
from reddit_sentiment_analysis.dashboard.app import run_gui
```

## Database Setup Module

**Removed:** March 2024

**Location:** `removed_modules/storage/setup_db.py`

**Reason for removal:**
The database setup module provided a dedicated CLI command for initializing the application's database. This functionality was redundant as the CommentDatabase class already handles database initialization automatically when the application starts.

**Original functionality:**

- Created SQLite database tables for storing comments and email confirmations
- Provided a CLI entry point for manual database setup

**Entry point (removed):**

```python
# From pyproject.toml
reddit-setup-db = "reddit_sentiment_analysis.storage.setup_db:main"
```

**Usage in code (removed):**

```python
# From interactive.py
from reddit_sentiment_analysis.storage.setup_db import main as setup_db_main
setup_db_main()
```

If this functionality needs to be reinstated, the files are preserved here for reference.
