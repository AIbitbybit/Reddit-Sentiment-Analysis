#!/usr/bin/env python3
"""
Test email sending in a production-like environment with full SSL verification.
This test simulates the exact conditions of the production environment.
"""

import asyncio
import getpass
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv, set_key

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Ensure we can import the app module
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import email service
from src.reddit_sentiment_analysis.email_service import EmailService


async def test_email_production():
    """Test sending an email with production settings (full SSL verification)."""
    print("=" * 60)
    print("PRODUCTION EMAIL TEST - WITH FULL SSL VERIFICATION".center(60))
    print("=" * 60)
    print(
        "\nThis test will verify email sending with production settings (full SSL verification)"
    )

    # Load environment variables
    load_dotenv()
    env_path = Path(__file__).parent.parent / ".env"

    # Temporarily set EMAIL_SKIP_VERIFY to false for this test
    original_value = os.environ.get("EMAIL_SKIP_VERIFY", "true")
    os.environ["EMAIL_SKIP_VERIFY"] = "false"

    try:
        # Get email settings
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = os.getenv("SMTP_PORT")
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("SENDER_EMAIL_PASSWORD")

        # Log email configuration (without password)
        print("\n=== Current Email Settings ===")
        print(f"SMTP Server: {smtp_server}")
        print(f"SMTP Port: {smtp_port}")
        print(f"Sender Email: {sender_email}")
        print(
            f"Password: {'*' * 8 if sender_password and sender_password != 'your_password_here' else 'Not set or using placeholder'}"
        )
        print(f"SSL Verification: Enabled (production mode)")

        # If password is not set or is the placeholder, prompt for it
        if not sender_password or sender_password == "your_password_here":
            print("\nEmail password is not set or is using the placeholder.")
            print(f"Please enter the password for {sender_email}:")
            sender_password = getpass.getpass("> ")

            # Update the password in memory
            os.environ["SENDER_EMAIL_PASSWORD"] = sender_password

            # Ask if user wants to save the password to .env
            print("\nDo you want to save this password to your .env file? (y/n)")
            print(
                "WARNING: This will store the password in plaintext in your .env file."
            )

            save_password = input("> ").lower() == "y"
            if save_password and env_path.exists():
                try:
                    set_key(str(env_path), "SENDER_EMAIL_PASSWORD", sender_password)
                    print("Password saved to .env file.")
                except Exception as e:
                    print(f"Failed to save password to .env file: {e}")

        # Check if email settings are configured
        if not all([smtp_server, smtp_port, sender_email, sender_password]):
            print("❌ ERROR: Email settings are not fully configured.")
            return False

        # Create test data
        print("\nEnter test email address to receive the test email:")
        test_recipient = input("> ")
        if not test_recipient:
            print("❌ ERROR: No recipient email provided. Test aborted.")
            return False

        # Confirm before proceeding
        print("\nProceed with test? This will send a real email. (y/n):")
        if input("> ").lower() != "y":
            print("Test cancelled by user.")
            return False

        # Create mock comment data
        comment_data = {
            "id": "test123",
            "comment_id": "test123",
            "subreddit": "TestSubreddit",
            "author": "TestUser",
            "body": "This is a test comment for email alert testing in production environment.",
            "created_utc": 1617293100,
            "permalink": "/r/TestSubreddit/comments/test123/comment/test123",
        }

        # Create mock sentiment result
        sentiment_result = {
            "sentiment": "negative",
            "confidence": 0.92,
        }

        # Create mock response
        suggested_response = "This is a test response to the negative comment. It's generated to test the email alert system in a production environment."

        # Initialize email service
        email_service = EmailService()

        # Send test email
        print(f"\n=== Sending Test Email ===")
        print(f"Sending to: {test_recipient}")
        print("Processing...")

        result = await email_service.send_alert(
            recipient=test_recipient,
            comment_data=comment_data,
            sentiment_result=sentiment_result,
            suggested_response=suggested_response,
        )

        if result:
            print("\n✅ SUCCESS: Email sent successfully with full SSL verification!")
            print(f"Please check {test_recipient} inbox for the test email.")
            return True
        else:
            print("\n❌ FAILED: Could not send email with full SSL verification.")
            print("Check the logs above for error details.")
            return False

    finally:
        # Restore original EMAIL_SKIP_VERIFY value
        os.environ["EMAIL_SKIP_VERIFY"] = original_value
        print("\n" + "=" * 60)
        print("TEST COMPLETED".center(60))
        print("=" * 60)


if __name__ == "__main__":
    try:
        # Run the test
        asyncio.run(test_email_production())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        logger.error(f"Error running email test: {str(e)}")
        import traceback

        traceback.print_exc()
