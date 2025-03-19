#!/usr/bin/env python
"""
Interactive script for Reddit Sentiment Analysis.
This script guides users through the setup and usage of the application.
"""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def clear_screen():
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    """Print the application header."""
    clear_screen()
    print("=" * 80)
    print(" " * 25 + "REDDIT SENTIMENT ANALYSIS" + " " * 25)
    print("=" * 80)
    print()


def check_env_file():
    """Check if the .env file exists and has the required variables."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.absolute()
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"

    if not env_file.exists():
        print("The .env file does not exist. Let's create one.")
        print(f"Using {env_example} as a template.")

        # Read the example file
        with open(env_example, "r") as f:
            env_content = f.read()

        # Create the .env file
        with open(env_file, "w") as f:
            f.write(env_content)

        print("The .env file has been created. Please edit it with your credentials.")
        print(
            "You can also configure all settings directly in the application's Settings tab."
        )
        print(f"File location: {env_file}")
        input("Press Enter to continue...")
        return False

    # Check if the .env file has the required variables
    with open(env_file, "r") as f:
        env_content = f.read()

    required_vars = [
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USER_AGENT",
        "OPENAI_API_KEY",
        "SMTP_SERVER",
        "SMTP_PORT",
        "SENDER_EMAIL",
        "SENDER_EMAIL_PASSWORD",
    ]

    missing_vars = []
    for var in required_vars:
        if var not in env_content or f"{var}=" in env_content:
            missing_vars.append(var)

    if missing_vars:
        print(
            "The following environment variables are missing or empty in your .env file:"
        )
        for var in missing_vars:
            print(f"- {var}")
        print(f"\nPlease edit the .env file at: {env_file}")
        print(
            "Alternatively, you can configure these settings directly in the application's Settings tab."
        )
        input("Press Enter to continue...")
        return False

    return True


def setup_database():
    """Set up the SQLite database."""
    print("Setting up the database...")
    try:
        # Use the CommentDatabase class to initialize the database
        from reddit_sentiment_analysis.storage.comment_db import CommentDatabase

        # Initialize the database
        db = CommentDatabase()
        print(f"Database setup complete at: {db.db_path}")
        return True
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        print(f"Error setting up database: {e}")
        return False


def run_monitoring_gui():
    """Run the monitoring GUI."""
    print("Starting the monitoring GUI...")
    try:
        # Try to use streamlit directly
        from reddit_sentiment_analysis.gui import run_gui

        run_gui()
        return True
    except Exception as e:
        logger.error(f"Error running monitoring GUI: {e}")
        print(f"Error running monitoring GUI: {e}")
        return False


def main_menu():
    """Display the main menu and handle user input."""
    while True:
        print_header()
        print("Main Menu:")
        print("1. Check environment setup")
        print("2. Set up database")
        print("3. Run monitoring GUI (includes Settings tab)")
        print("0. Exit")

        choice = input("\nEnter your choice (0-3): ")

        if choice == "1":
            check_env_file()
        elif choice == "2":
            setup_database()
        elif choice == "3":
            run_monitoring_gui()
        elif choice == "0":
            print("Exiting the application. Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please try again.")

        input("\nPress Enter to continue...")
        clear_screen()


def run():
    """Run the interactive script."""
    try:
        print_header()
        print("Welcome to Reddit Sentiment Analysis!")
        print(
            "This interactive script will guide you through the setup and usage of the application."
        )
        print(
            "The application now includes a Settings tab where you can configure all necessary settings."
        )
        print()
        input("Press Enter to continue...")

        main_menu()

    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
