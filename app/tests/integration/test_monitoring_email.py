#!/usr/bin/env python3
"""
Integration test for monitoring system's email service.
Tests sending emails for negative comment alerts.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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

# Import the necessary components
from app.src.reddit_sentiment_analysis.email_service import EmailService
from app.src.reddit_sentiment_analysis.storage.comment_db import CommentDatabase


async def main():
    print("=" * 60)
    print("EMAIL SERVICE FOR NEGATIVE COMMENTS".center(60))
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

    # Initialize services
    print("\n=== Initializing Services ===")
    db = CommentDatabase()
    email_service = EmailService()

    # Create test comment data
    comment_data = {
        "id": "test_integration_id",
        "comment_id": "test_comment_id",
        "subreddit": "IntegrationTest",
        "author": "test_integration_user",
        "body": "This is a test comment for the integration test. The service is terrible.",
        "permalink": "https://www.reddit.com/r/testsubreddit/comments/test",
        "created_utc": time.time(),
    }

    # Create sentiment result
    sentiment_result = {
        "sentiment": "negative",
        "confidence": 0.85,
        "explanation": "The comment contains negative language about the service.",
    }

    # Generate response
    suggested_response = "I'm sorry to hear that you're experiencing issues with our service. We'd like to help resolve this. Could you please provide more details about the specific problems you're facing? Our team is ready to assist you."

    # Store in database
    print("\n=== Storing Test Comment in Database ===")
    db.add_comment(
        comment_data=comment_data,
        key_term="service",
        sentiment="negative",
        confidence=0.85,
        ai_response=suggested_response,
        status="pending_approval",
    )
    print("Comment stored in database.")

    # Send email alert
    print("\n=== Sending Email Alert ===")
    print(f"Sending email to {TEST_RECIPIENT}...")

    # Send the email alert
    success = await email_service.send_alert(
        recipient=TEST_RECIPIENT,
        comment_data=comment_data,
        sentiment_result=sentiment_result,
        suggested_response=suggested_response,
    )

    if success:
        print("\n✅ SUCCESS: Email alert sent successfully!")
        print(f"Please check {TEST_RECIPIENT} inbox for the test email.")

        # Update database to mark email as sent
        db.mark_email_sent(
            comment_id="test_integration_id", email_recipient=TEST_RECIPIENT
        )
        print("Database updated to mark email as sent.")
    else:
        print("\n❌ FAILED: Email alert could not be sent.")
        print("Check the logs above for error details.")

    print("\n" + "=" * 60)
    print("TEST COMPLETED".center(60))
    print("=" * 60)


# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
