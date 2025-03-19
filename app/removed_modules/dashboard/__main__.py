"""
Main entry point for the dashboard.
"""

import os
import sys
from pathlib import Path

import streamlit.web.cli as stcli

# Get the path to the app.py file
app_path = Path(__file__).parent / "app.py"

if __name__ == "__main__":
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.port=8501",
        "--server.address=0.0.0.0",
    ]
    sys.exit(stcli.main())
