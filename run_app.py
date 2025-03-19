#!/usr/bin/env python3
"""
Reddit Sentiment Analysis - Application Runner

This script runs the Reddit Sentiment Analysis application with proper configuration.
"""

import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("app_runner")

# Make sure the application can be imported
app_dir = Path(__file__).resolve().parent
sys.path.append(str(app_dir))

# Import the GUI runner
from app.src.reddit_sentiment_analysis.gui import run_gui

if __name__ == "__main__":
    print("=" * 80)
    print("REDDIT SENTIMENT ANALYSIS".center(80))
    print("=" * 80)
    print("\nStarting application...")

    # Set environment variable to suppress Streamlit's browser opening
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "false"

    # Run the GUI
    run_gui()
