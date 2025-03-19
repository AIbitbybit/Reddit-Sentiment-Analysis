#!/usr/bin/env python
"""
Test the EmailService class directly from the application code.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("email_service_test")

# Load environment variables
load_dotenv()

# Set SSL verification to be skipped for testing
os.environ["EMAIL_SKIP_VERIFY"] = "true"

# Make sure package is importable
# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[2]  # app directory
sys.path.append(str(project_root.parent))  # main project directory

# Import the EmailService
from app.src.reddit_sentiment_analysis.email_service import EmailService


# Main async function
async def main():
    print("=" * 60)
    print("EMAIL SERVICE TEST".center(60))
    print("=" * 60)

    # Ask for test recipient email
    print("\nEnter recipient email for test (or press Enter to use test@example.com):")
    TEST_RECIPIENT = input("> ").strip() or "test@example.com"

    # Print current settings
    print("\n=== Current Email Settings ===")
    print(f"SMTP Server: {os.getenv('SMTP_SERVER')}")
    print(f"SMTP Port: {os.getenv('SMTP_PORT')}")
    print(f"Sender Email: {os.getenv('SENDER_EMAIL')}")
    print(f"Password: {'*' * 8 if os.getenv('SENDER_EMAIL_PASSWORD') else 'Not set'}")
    print(f"Test Recipient: {TEST_RECIPIENT}")
    print(f"Skip SSL Verification: {os.getenv('EMAIL_SKIP_VERIFY')}")

    # Confirm before proceeding
    print("\nProceed with test? (y/n):")
    if input("> ").lower() != "y":
        print("Test cancelled.")
        return

    # Initialize EmailService
    print("\n=== Initializing EmailService ===")
    email_service = EmailService()

    # Create test comment data
    comment_data = {
        "id": "test_id",
        "subreddit": "testsubreddit",
        "author": "test_author",
        "body": "This is a test comment with negative sentiment.",
        "permalink": "https://www.reddit.com/r/testsubreddit/comments/test",
    }

    # Create test sentiment result
    sentiment_result = {
        "sentiment": "negative",
        "confidence": 0.95,
        "explanation": "The comment has a negative tone.",
    }

    # Create test AI response
    ai_response = "I'm sorry to hear that you're experiencing issues. This is a test AI response to a negative comment."

    # Send test email
    print("\n=== Sending Test Email ===")
    print(f"Sending email to {TEST_RECIPIENT}...")

    success = await email_service.send_alert(
        recipient=TEST_RECIPIENT,
        comment_data=comment_data,
        sentiment_result=sentiment_result,
        suggested_response=ai_response,
    )

    if success:
        print("\n✅ SUCCESS: Email sent successfully!")
        print(f"Please check {TEST_RECIPIENT} inbox for the test email.")
    else:
        print("\n❌ FAILED: Email could not be sent.")
        print("Check the logs above for error details.")

    print("\n" + "=" * 60)
    print("TEST COMPLETED".center(60))
    print("=" * 60)


# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
