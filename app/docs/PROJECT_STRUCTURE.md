# Reddit Sentiment Analysis Project Structure

This document provides an overview of the project structure and organization.

## Directory Structure

```
Reddit-Sentiment-Analysis-draft/    # Project root
└── app/                         # Application code
    ├── src/                     # Source code
    │   └── reddit_sentiment_analysis/
    │       ├── __init__.py
    │       ├── __main__.py        # Entry point for running as a module
    │       ├── config.py          # Configuration settings
    │       ├── email_service.py   # Email functionality
    │       ├── gui.py             # Streamlit GUI
    │       ├── interactive.py     # Interactive setup
    │       ├── monitoring.py      # Reddit monitoring
    │       ├── response_generator.py # AI response generation
    │       │
    │       ├── analysis/          # Sentiment analysis components
    │       ├── data_collection/   # Reddit data collection components
    │       │   ├── __init__.py
    │       │   ├── cli.py         # Command-line interface for data collection
    │       │   ├── collector.py   # Data collection core functionality
    │       │   └── reddit_client.py # Reddit API client
    │       │
    │       ├── preprocessing/     # Data preprocessing utilities
    │       ├── storage/           # Database and storage components
    │       │   ├── __init__.py
    │       │   ├── comment_db.py  # SQLite database for comments
    │       │   └── vector_store.py # Vector database functionality
    │       │
    │       └── utils/            # Utility functions and helpers
    │
    ├── tests/                     # Tests directory
    │   ├── __init__.py
    │   ├── unit/                  # Unit tests
    │   │   ├── test_duration_format.py
    │   │   └── test_email_service.py
    │   │
    │   ├── integration/           # Integration tests
    │   │   ├── test_monitoring_threads.py
    │   │   ├── test_monitoring_email.py
    │   │   ├── test_new_email_flow.py
    │   │   └── test_reddit_oauth.py
    │   │
    │   └── utils/                 # Test utilities
    │       ├── test_hostinger_email.py
    │       └── test_hostinger_email_secure.py
    │
    ├── scripts/                   # Utility scripts
    │   ├── email_debug.py         # Email debugging utility
    │   ├── manual_auth.py         # Manual Reddit authentication
    │   ├── setup_reddit_oauth.py  # Reddit OAuth setup
    │   ├── verify_reddit_app.py   # Reddit app verification
    │   └── cleanup.py             # Data and log cleanup utility
    │
    ├── docs/                      # Documentation
    │   ├── EMAIL_CONFIG.md        # Email configuration guide
    │   └── PROJECT_STRUCTURE.md   # This file
    │
    ├── data/                      # Data storage
    │   ├── comments.db            # SQLite database for comments
    │   ├── raw/                   # Raw data storage
    │   └── vector_db/             # Vector database storage
    │
    ├── logs/                      # Application logs
    │   └── app_log.txt            # Main application log
    │
    ├── backups/                   # Backup storage
    │   ├── logs/                  # Log archives
    │   ├── database/              # Database backups
    │   └── vector_db/             # Vector database backups
    │
    ├── .env                       # Environment variables (not in version control)
    ├── .env.example               # Example environment variables
    ├── .gitignore                 # Git ignore file
    ├── install.bat                # Windows installation script
    ├── install.sh                 # Unix installation script
    ├── poetry.lock                # Poetry dependencies lock file
    ├── pyproject.toml             # Project metadata and dependencies
    ├── README.md                  # Project documentation
    └── run_app.py                 # Application launcher script
```

## Key Components

### Source Code (`src/`)

The source code is organized into modular components:

- **Core functionality**: Files in the root `reddit_sentiment_analysis` directory handle the main application logic.
- **Data Collection**: The `data_collection` package contains Reddit API integration.
- **Storage**: The `storage` package handles database operations and vector storage.
- **Analysis**: The `analysis` package contains sentiment analysis logic.

### Tests (`tests/`)

Tests are organized by type:

- **Unit Tests**: Tests for individual components in isolation.
- **Integration Tests**: Tests that verify interactions between components.
- **Utilities**: Test helpers and specific test cases for external services.

### Scripts (`scripts/`)

Utility scripts for various operations:

- Email debugging and testing
- Reddit API authentication
- Setup and verification utilities
- Data and log cleanup

### Documentation (`docs/`)

Project documentation, including:

- Email configuration guide
- Project structure and organization
- Additional documentation files

### Data (`data/`)

Storage for application data:

- SQLite database for comment storage
- Vector database for semantic search
- Raw collected data

### Logs (`logs/`)

Application logs and diagnostics:

- Runtime logs
- Error tracking
- Performance metrics

### Backups (`backups/`)

Automated backups created by the cleanup script:

- Archived log files
- Database backups
- Vector database snapshots

## Installation and Setup

- `install.sh` and `install.bat`: Platform-specific installation scripts
- `.env.example`: Template for required environment variables
- `run_app.py`: Launcher for the Streamlit application
