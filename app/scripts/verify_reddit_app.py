#!/usr/bin/env python
"""
A utility script to verify Reddit API settings and provide guidance on fixing OAuth issues.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed, using existing environment variables")

# Get settings from environment
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_REDIRECT_URI = os.getenv("REDDIT_REDIRECT_URI", "http://localhost:8080")


def verify_settings():
    """Verify Reddit API settings and provide guidance."""
    print("\n===== Reddit App Settings Verification =====\n")

    # Check client ID
    if not REDDIT_CLIENT_ID:
        print(
            "❌ REDDIT_CLIENT_ID is not set in your environment variables or .env file"
        )
    else:
        print(
            f"✅ REDDIT_CLIENT_ID: {'*' * 5}{REDDIT_CLIENT_ID[-4:] if len(REDDIT_CLIENT_ID) > 4 else REDDIT_CLIENT_ID}"
        )

    # Check client secret
    if not REDDIT_CLIENT_SECRET:
        print(
            "❌ REDDIT_CLIENT_SECRET is not set in your environment variables or .env file"
        )
    else:
        print(
            f"✅ REDDIT_CLIENT_SECRET: {'*' * 5}{REDDIT_CLIENT_SECRET[-4:] if len(REDDIT_CLIENT_SECRET) > 4 else REDDIT_CLIENT_SECRET}"
        )

    # Check redirect URI
    if not REDDIT_REDIRECT_URI:
        print(
            "❌ REDDIT_REDIRECT_URI is not set in your environment variables or .env file"
        )
    else:
        print(f"✅ REDDIT_REDIRECT_URI: {REDDIT_REDIRECT_URI}")

        # Parse the redirect URI to provide better guidance
        try:
            parts = urlparse(REDDIT_REDIRECT_URI)
            hostname = parts.netloc.split(":")[0]
            port = parts.netloc.split(":")[1] if ":" in parts.netloc else "80"

            print(f"   - Hostname: {hostname}")
            print(f"   - Port: {port}")

            if hostname != "localhost" and hostname != "127.0.0.1":
                print(
                    "⚠️  Warning: Reddit typically requires 'localhost' or '127.0.0.1' for the redirect URI hostname for installed apps"
                )
        except Exception as e:
            print(f"⚠️  Warning: Could not parse the redirect URI: {e}")

    print("\n===== Action Items =====\n")
    print("1. Go to https://www.reddit.com/prefs/apps")
    print("2. Find your Reddit application (or create a new one)")
    print("3. Ensure your application settings match the following:")
    print("   - App type: Web app")
    print(f"   - Redirect URI: {REDDIT_REDIRECT_URI}")
    print("4. After updating, click 'update app' to save the changes")
    print("\n===== Common OAuth Issues =====\n")
    print("If you're seeing 'received 400 HTTP response' errors:")
    print(
        "- Make sure the redirect URI in your Reddit app settings EXACTLY matches what's in your .env file"
    )
    print("- Double-check your client ID and client secret for typos")
    print(
        "- Ensure your Reddit app is set as a 'web app' type, not a script or installed app"
    )
    print("- Try deleting any existing token file and re-authenticating")
    print(
        "\nTip: Reddit's OAuth implementation is very strict about redirect URI matching!"
    )

    print("\n===== Next Steps =====\n")
    print(
        "After confirming your Reddit app settings are correct, run the authentication test:"
    )
    print("python test_reddit_oauth.py --verbose --force-auth")


if __name__ == "__main__":
    verify_settings()
