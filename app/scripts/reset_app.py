#!/usr/bin/env python3
"""
Script to reset the application without requiring user confirmation.
This can be called from other scripts or processes to automate the reset.
"""

import logging
import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

# Import from our script that does the work
from scripts.recreate_database import clean_start

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def reset_application():
    """Reset the application's database and state without requiring user confirmation."""
    print("Resetting the application...")

    # Perform the clean start
    success = clean_start()

    if success:
        print("Application successfully reset!")
        return 0
    else:
        print("Failed to reset application. Check the logs for details.")
        return 1


if __name__ == "__main__":
    # Exit with appropriate status code
    sys.exit(reset_application())
