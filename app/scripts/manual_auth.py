#!/usr/bin/env python
"""
Manual Reddit OAuth Authorization Script

This script helps you manually get a Reddit OAuth token without relying on a callback server.
It will generate an authorization URL for you to open in your browser and then guide you
through entering the authorization code.
"""

import json
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed, using existing environment variables")

import praw
from prawcore.exceptions import ResponseException

# Define token path
TOKEN_PATH = Path(__file__).parent / "reddit_token.json"


def create_reddit_instance():
    """Create a Reddit instance with credentials from environment."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv(
        "REDDIT_USER_AGENT", "python:reddit-sentiment-analysis:v0.1.0"
    )
    redirect_uri = os.getenv("REDDIT_REDIRECT_URI", "http://localhost:8080")

    if not client_id or not client_secret:
        print("ERROR: Missing Reddit API credentials in .env file")
        sys.exit(1)

    # Print the credentials being used (partially masked)
    print(f"Using Client ID: {'*' * (len(client_id) - 4)}{client_id[-4:]}")
    print(f"Using Client Secret: {'*' * (len(client_secret) - 4)}{client_secret[-4:]}")
    print(f"Using Redirect URI: {redirect_uri}")

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        user_agent=user_agent,
    )


def generate_auth_url(reddit):
    """Generate the authorization URL."""
    scopes = ["identity", "read", "submit"]
    print("\nGenerating authorization URL...")
    return reddit.auth.url(scopes, "RANDOM_STATE", "permanent")


def get_token(reddit, code):
    """Exchange the authorization code for a token."""
    try:
        print("\nExchanging code for token...")
        refresh_token = reddit.auth.authorize(code)

        # Save the token
        token_data = {"refresh_token": refresh_token}
        with open(TOKEN_PATH, "w") as f:
            json.dump(token_data, f)

        print(f"✅ Success! Token saved to {TOKEN_PATH}")

        # Verify the token works
        username = reddit.user.me().name
        print(f"✅ Successfully authenticated as u/{username}")
        return True
    except ResponseException as e:
        print(f"❌ Error: {e}")
        if hasattr(e, "response") and e.response.status_code == 400:
            print("\nCommon reasons for 400 Bad Request errors:")
            print("1. The authorization code was copied incorrectly")
            print("2. The code has expired (they expire quickly)")
            print(
                "3. The redirect URI doesn't exactly match what's in your Reddit app settings"
            )
            print("4. Your Reddit app isn't configured as a 'web app' type")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def process_authorization_code(code):
    """Process the authorization code from user input."""
    # Clean up the code
    if "#" in code:
        code = code.split("#")[0]
        print("Removed # fragment from code")

    # Try to extract just the code from a full URL or code=X format
    if "code=" in code:
        try:
            if "?" in code and "&" in code:
                params = code.split("?")[1].split("&")
                for param in params:
                    if param.startswith("code="):
                        code = param.split("=")[1]
                        break
            elif "code=" in code:
                code = (
                    code.split("code=")[1].split("&")[0]
                    if "&" in code
                    else code.split("code=")[1]
                )
            print(f"Extracted code: {code[:5]}...{code[-5:] if len(code) > 10 else ''}")
        except Exception:
            print("Could not extract code from input, using as-is")

    return code.strip()


def main():
    """Main function."""
    print("\n===== REDDIT OAUTH MANUAL SETUP =====\n")

    # Check if token already exists
    if TOKEN_PATH.exists():
        print(f"Warning: Token file already exists at {TOKEN_PATH}")
        response = input("Delete existing token and continue? (y/n): ").strip().lower()
        if response == "y":
            TOKEN_PATH.unlink()
            print("Existing token deleted")
        else:
            print("Keeping existing token. Exiting...")
            return

    # Create Reddit instance
    reddit = create_reddit_instance()

    # Generate authorization URL
    auth_url = generate_auth_url(reddit)

    # Display instructions
    print("\n===== STEP 1: AUTHORIZE THE APPLICATION =====")
    print("\nPlease copy and paste this URL into your browser:")
    print(f"\n{auth_url}\n")
    print("After opening the URL:")
    print("1. Log in to Reddit if prompted")
    print("2. Click 'Allow' to authorize the application")
    print("3. You will be redirected to a URL that may show an error page")
    print("4. That's OK! Look in your browser's address bar")
    print("5. The URL will contain 'code=XXXX' - this is your authorization code")

    # Get the code from the user
    print("\n===== STEP 2: ENTER THE AUTHORIZATION CODE =====\n")
    print("After authorizing, copy the full URL from your browser's address bar")
    print("or just the code part after 'code=' and before any '&' or '#' character")

    code = input("\nEnter the authorization code or full URL: ").strip()
    if not code:
        print("No code entered. Exiting...")
        return

    # Process the code
    processed_code = process_authorization_code(code)

    # Exchange the code for a token
    success = get_token(reddit, processed_code)

    if success:
        print(
            "\n🎉 OAuth setup complete! You can now use the application to post comments."
        )
    else:
        print("\n❌ OAuth setup failed. Please try again.")
        print("Verify your app settings at https://www.reddit.com/prefs/apps")
        print(
            "Make sure it's a 'web app' type with redirect URI: http://localhost:8080"
        )


if __name__ == "__main__":
    main()
