#!/usr/bin/env python
"""
Launcher script for the Reddit Sentiment Analysis application.
This script launches the Streamlit GUI directly.
"""

import os
import shutil
import subprocess
import sys


def check_streamlit():
    """Check if Streamlit is installed."""
    return shutil.which("streamlit") is not None


def check_environment():
    """Check if the environment is properly set up."""
    # Check if .env file exists
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_file = os.path.join(script_dir, ".env")
    env_example = os.path.join(script_dir, ".env.example")

    if not os.path.exists(env_file):
        print("Warning: .env file not found. Creating from template...")
        if os.path.exists(env_example):
            with open(env_example, "r") as src, open(env_file, "w") as dst:
                dst.write(src.read())
            print(f"Created .env file. Please edit {env_file} with your credentials.")
            print(
                "You can also configure settings directly in the application's Settings tab."
            )
        else:
            print(f"Error: Could not find .env.example template at {env_example}")
            return False

    return True


def main():
    """Launch the Streamlit GUI directly."""
    # Get the path to the gui.py file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gui_path = os.path.join(script_dir, "src", "reddit_sentiment_analysis", "gui.py")

    # Make sure the path exists
    if not os.path.exists(gui_path):
        print(f"Error: Could not find {gui_path}")
        return 1

    # Check if Streamlit is installed
    if not check_streamlit():
        print("Error: Streamlit is not installed or not in PATH.")
        print("Please install it with: pip install streamlit")
        return 1

    # Check environment setup
    if not check_environment():
        print("Warning: Environment setup is incomplete.")
        print("The application may not function correctly.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != "y":
            return 1

    # Launch Streamlit directly
    print("Launching Reddit Sentiment Monitor GUI...")
    print("You can configure all settings in the Settings tab of the application.")
    try:
        result = subprocess.run(["streamlit", "run", gui_path])
        return result.returncode
    except KeyboardInterrupt:
        print("\nApplication stopped by user.")
        return 0
    except Exception as e:
        print(f"Error launching application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
