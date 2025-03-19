#!/usr/bin/env python
"""
Test the new email notification flow that directs users to the application.
This script sends a test email with the new format.
"""

import logging
import os
import sys
import time

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("email_flow_test")

# Load environment variables
load_dotenv()

# Make sure package is importable
sys.path.append(os.path.abspath("./"))

# Import the EmailService
from src.reddit_sentiment_analysis.email_service import EmailService

print("=" * 60)
print("NEW EMAIL NOTIFICATION FLOW TEST".center(60))
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
print(f"Application URL: {os.getenv('APP_URL', 'http://localhost:8501')}")
print(f"Test Recipient: {TEST_RECIPIENT}")

# Confirm before proceeding
print("\nProceed with test? (y/n):")
if input("> ").lower() != "y":
    print("Test cancelled.")
    sys.exit(0)

# Initialize EmailService
print("\n=== Initializing EmailService ===")
email_service = EmailService()

# Create test comment data
print("\n=== Creating test negative comment ===")
comment_data = {
    "id": f"t1_test_{int(time.time())}",
    "comment_id": f"test_{int(time.time())}",
    "subreddit": "testsubreddit",
    "author": "test_author",
    "body": "This is a test comment with negative sentiment for testing the new email flow.",
    "created_utc": time.time(),
    "permalink": "https://www.reddit.com/r/testsubreddit/comments/test",
    "sentiment": "negative",
    "confidence": 0.95,
}

# Create test AI response
ai_response = "I'm sorry to hear that you're experiencing issues. This is a test AI response to a negative comment. We're here to help resolve your concerns."

# Send test email
print("\n=== Sending Test Email Alert ===")
print(f"Sending email to {TEST_RECIPIENT}...")

success = email_service.send_alert(TEST_RECIPIENT, comment_data, ai_response)

if success:
    print("\n✅ SUCCESS: Email alert sent successfully!")
    print(f"Please check {TEST_RECIPIENT} inbox for the test email.")
    print(
        "The email should now contain a link to the application instead of asking for a reply."
    )
    print(
        f"The application URL in the email is: {os.getenv('APP_URL', 'http://localhost:8501')}"
    )
else:
    print("\n❌ FAILED: Email alert could not be sent.")
    print("Check the logs above for error details.")

print("\n" + "=" * 60)
print("TEST COMPLETED".center(60))
print("=" * 60)
