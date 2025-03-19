#!/usr/bin/env python
"""
Reddit OAuth Setup Script

This script helps you set up OAuth authentication for your Reddit app.
It provides a step-by-step guide to ensure your Reddit app is correctly
configured and helps you authenticate with Reddit to generate and save
a refresh token for future API access.
"""

import json
import logging
import os
import sys
import webbrowser
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("reddit_oauth_setup")

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    logger.warning("python-dotenv not installed, using existing environment variables")

# Import the RedditClient and TOKEN_PATH
try:
    from src.reddit_sentiment_analysis.data_collection.reddit_client import (
        TOKEN_PATH,
        RedditClient,
    )
except ImportError:
    logger.error(
        "Failed to import RedditClient. Make sure the package is installed correctly."
    )
    sys.exit(1)


def verify_reddit_app_settings():
    """Verify and display Reddit app settings."""
    print("\n=== Reddit App Settings ===\n")

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    redirect_uri = os.getenv("REDDIT_REDIRECT_URI", "http://localhost:8080")

    if not client_id:
        print("❌ REDDIT_CLIENT_ID is not set in .env file")
        return False
    else:
        print(f"✅ Client ID: {'*' * (len(client_id) - 4)}{client_id[-4:]}")

    if not client_secret:
        print("❌ REDDIT_CLIENT_SECRET is not set in .env file")
        return False
    else:
        print(f"✅ Client Secret: {'*' * (len(client_secret) - 4)}{client_secret[-4:]}")

    print(f"✅ Redirect URI: {redirect_uri}")

    print("\n✨ Validating token path...")
    token_dir = TOKEN_PATH.parent
    if not token_dir.exists():
        print(f"Creating directory: {token_dir}")
        token_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Token will be saved to: {TOKEN_PATH}")

    if TOKEN_PATH.exists():
        print(f"ℹ️ Existing token found. It will be replaced if you continue.")
        delete = input("Delete existing token? (y/n): ").strip().lower()
        if delete == "y":
            TOKEN_PATH.unlink()
            print("✅ Existing token deleted")

    return True


def display_app_setup_instructions():
    """Display instructions for setting up a Reddit app."""
    print("\n=== How to Set Up Your Reddit App ===\n")
    print("1. Go to https://www.reddit.com/prefs/apps")
    print("2. Scroll down to the bottom and click 'create another app...'")
    print("3. Fill in the following:")
    print("   - Name: Any name you want for your app")
    print("   - Select 'web app' (this is CRITICAL)")
    print("   - Description: Optional description")
    print("   - About URL: Can be left blank")
    print("   - Redirect URI: http://localhost:8080 (MUST match exactly)")
    print("4. Click 'create app'")
    print("5. Copy the Client ID (the string under the app name)")
    print("6. Copy the Client Secret")
    print("\nUpdate these values in your .env file:\n")
    print("REDDIT_CLIENT_ID=your_client_id")
    print("REDDIT_CLIENT_SECRET=your_client_secret")
    print("REDDIT_REDIRECT_URI=http://localhost:8080")
    print("\nAfter updating the .env file, run this script again.")


def setup_oauth():
    """Guide the user through the OAuth setup process."""

    # Get redirect URI from environment
    redirect_uri = os.getenv("REDDIT_REDIRECT_URI", "http://localhost:8080")

    # Create a Reddit client instance
    client = RedditClient()

    # Generate and display the authorization URL
    print("\n=== Step 1: Authorize Your Application ===\n")
    print("A browser window will open with the Reddit authorization page.")
    print("Please log in to Reddit (if not already logged in) and click 'Allow'.")
    print(
        "\nAfter authorizing, you will be redirected to a page that might show an error."
    )
    print("This is NORMAL because localhost:8080 is not running a web server.")
    print("\nIMPORTANT: Look at the URL in your browser's address bar.")
    print("You will need to copy the 'code' parameter from the URL in the next step.")

    input("\nPress Enter to open the authorization page in your browser...")

    # Get the authorization URL and open it
    auth_url = client.reddit.auth.url(
        scopes=["identity", "read", "submit"],
        state="sentinel",
        redirect_uri=redirect_uri,
    )
    print(f"Opening URL: {auth_url}")
    webbrowser.open(auth_url)

    print("\n=== Step 2: Copy the Authorization Code ===\n")
    print(
        "After authorizing, your browser will be redirected to a URL that looks like:"
    )
    print(f"{redirect_uri}?code=YOUR_CODE_HERE&state=sentinel")
    print(
        "\nCopy the part that says 'YOUR_CODE_HERE' (the actual code will be a random string)"
    )

    # Get the authorization code from the user
    code = input("\nPaste the authorization code here: ").strip()

    # Clean up the code
    if "#" in code:
        code = code.split("#")[0]

    if "code=" in code:
        # Extract just the code part
        try:
            # Try to extract from a full URL
            if "?" in code and "&" in code:
                params = code.split("?")[1].split("&")
                for param in params:
                    if param.startswith("code="):
                        code = param.split("=")[1]
                        break
            # Or just from the code= part
            elif "code=" in code:
                code = (
                    code.split("code=")[1].split("&")[0]
                    if "&" in code
                    else code.split("code=")[1]
                )
        except Exception:
            print("⚠️ Could not parse the code from your input. Using the raw input.")

    print(f"\nUsing code: {code[:5]}... (length: {len(code)})")

    # Exchange the code for a token
    print("\n=== Step 3: Exchanging Authorization Code for Token ===\n")
    print("Attempting to exchange your authorization code for a refresh token...")

    try:
        # Create a new Reddit instance for token exchange with explicit redirect URI
        import praw

        reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv(
                "REDDIT_USER_AGENT", "python:reddit-sentiment-analysis:v0.1.0"
            ),
            redirect_uri=redirect_uri,
        )

        # Exchange the code for a refresh token
        refresh_token = reddit.auth.authorize(code)

        # Save the token
        token_data = {"refresh_token": refresh_token}
        with open(TOKEN_PATH, "w") as f:
            json.dump(token_data, f)

        print("✅ Success! Refresh token saved successfully.")

        # Verify the token works
        print("\n=== Step 4: Verifying Authentication ===\n")
        print("Checking if authentication worked...")

        username = reddit.user.me().name
        print(f"✅ Successfully authenticated as u/{username}")

        print(
            "\n🎉 OAuth setup complete! You can now use the application with full permissions."
        )
        return True

    except Exception as e:
        print(f"❌ Error exchanging authorization code: {str(e)}")
        print("\nCommon reasons for failure:")
        print("1. The authorization code was incorrect or expired")
        print("2. The Reddit app is not configured correctly (must be a 'web app')")
        print(
            "3. The redirect URI doesn't exactly match what's in your Reddit app settings"
        )
        print("4. Client ID or Client Secret is incorrect")

        print("\nPlease verify your app settings at https://www.reddit.com/prefs/apps")
        print("and try again.")
        return False


def main():
    """Main function to run the OAuth setup."""
    print("\n" + "=" * 80)
    print("REDDIT OAUTH SETUP".center(80))
    print("=" * 80 + "\n")

    print("This script will help you set up OAuth authentication for your Reddit app.")
    print(
        "This is required to post comments and perform other actions that need authentication."
    )

    # Verify app settings
    if not verify_reddit_app_settings():
        print("\n❌ Reddit app settings are incomplete or incorrect.")
        display_app_setup_instructions()
        return

    # Check if user wants to continue
    continue_setup = input("\nContinue with OAuth setup? (y/n): ").strip().lower()
    if continue_setup != "y":
        print("\nSetup cancelled. You can run this script again later.")
        return

    # Run the OAuth setup
    if setup_oauth():
        print("\nNext steps:")
        print("1. Run the application normally")
        print("2. You should now be able to post comments via the application")
    else:
        print("\nOAuth setup failed. Please try again after fixing the issues.")


if __name__ == "__main__":
    main()
