#!/usr/bin/env python
"""
Hostinger Email Test Script
This script tests sending an email using Hostinger SMTP settings.
"""

import logging
import os
import smtplib
import ssl
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("hostinger_email_test")

# Set to True to show detailed SMTP communication
DEBUG_MODE = True

from dotenv import load_dotenv

print("=" * 60)
print("HOSTINGER EMAIL TEST".center(60))
print("=" * 60)

# Load environment variables
load_dotenv()

# Get email settings from .env file
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.hostinger.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_EMAIL_PASSWORD")

# Ask for test recipient email
print("\nEnter recipient email for test (or press Enter to use test@example.com):")
TEST_RECIPIENT = input("> ").strip() or "test@example.com"

# Print current settings
print("\n=== Current Settings ===")
print(f"SMTP Server: {SMTP_SERVER}")
print(f"SMTP Port: {SMTP_PORT}")
print(f"Sender Email: {SENDER_EMAIL}")
print(f"Password: {'*' * 8 if SENDER_PASSWORD else 'Not set'}")
print(f"Test Recipient: {TEST_RECIPIENT}")

# Check if settings are missing
if not all([SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD]):
    print("\n⚠️ WARNING: Some email settings are missing. Please check your .env file.")
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("❌ ERROR: Email credentials are required. Test cannot continue.")
        sys.exit(1)

# Ask if user wants to disable SSL verification
print("\nWould you like to skip SSL certificate verification?")
print("This can help if you're getting SSL certificate verification errors (y/n):")
SKIP_SSL_VERIFICATION = input("> ").lower() == "y"

# Confirm before proceeding
print("\nProceed with test? (y/n):")
if input("> ").lower() != "y":
    print("Test cancelled.")
    sys.exit(0)

# Create test email
msg = MIMEMultipart()
msg["Subject"] = "Hostinger Email Test - Reddit Sentiment Analysis"
msg["From"] = SENDER_EMAIL
msg["To"] = TEST_RECIPIENT

# Email body
body = f"""
<html>
<body>
    <h2>Hostinger Email Test</h2>
    <p>This is a test email from the Reddit Sentiment Analysis application.</p>
    <p>If you're seeing this, email sending with Hostinger is working correctly!</p>
    <p><strong>Settings used:</strong></p>
    <ul>
        <li>SMTP Server: {SMTP_SERVER}</li>
        <li>SMTP Port: {SMTP_PORT}</li>
        <li>Sender Email: {SENDER_EMAIL}</li>
        <li>SSL Verification: {'Disabled' if SKIP_SSL_VERIFICATION else 'Enabled'}</li>
    </ul>
    <p>Timestamp: {time.ctime()}</p>
</body>
</html>
"""

msg.attach(MIMEText(body, "html"))

# Test sending email
print("\n=== Testing Email Sending ===")
print(f"Connecting to {SMTP_SERVER}:{SMTP_PORT} using SSL...")

try:
    # Create SSL context
    context = ssl.create_default_context()

    # Disable certificate verification if requested
    if SKIP_SSL_VERIFICATION:
        print("⚠️  SSL certificate verification disabled")
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    # Connect to the server
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        if DEBUG_MODE:
            server.set_debuglevel(1)  # Enable debug output

        print(f"Authenticating as {SENDER_EMAIL}...")
        server.login(SENDER_EMAIL, SENDER_PASSWORD)

        print(f"Sending test email to {TEST_RECIPIENT}...")
        server.send_message(msg)

        print("\n✅ SUCCESS: Email sent successfully!")
        print(f"Please check {TEST_RECIPIENT} inbox for the test email.")

except ssl.SSLError as e:
    print(f"\n❌ SSL ERROR: {str(e)}")
    print("This may indicate an SSL/TLS configuration issue.")
    print("Suggestions:")
    print("- Try again with SSL certificate verification disabled (y)")
    print("- Make sure you're using port 465 for SSL connections")
    print("- Check if your network blocks SSL connections")
    print("- Try updating your SSL certificates")

except smtplib.SMTPAuthenticationError as e:
    print(f"\n❌ AUTHENTICATION ERROR: {str(e)}")
    print("This suggests your email credentials are incorrect.")
    print("Suggestions:")
    print("- Double-check your email address and password")
    print("- Make sure your Hostinger email account is active")
    print("- Check if there are any security settings that might block this connection")

except smtplib.SMTPConnectError as e:
    print(f"\n❌ CONNECTION ERROR: {str(e)}")
    print("Unable to connect to the SMTP server.")
    print("Suggestions:")
    print("- Verify the SMTP server address (should be smtp.hostinger.com)")
    print("- Check your internet connection")
    print("- Check if your ISP blocks outgoing SMTP traffic")

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback

    print("\nDetailed error information:")
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETED".center(60))
print("=" * 60)

# Offer to update .env file if necessary
if (
    SKIP_SSL_VERIFICATION
    and input(
        "\nUpdate application to permanently disable SSL verification? (y/n): "
    ).lower()
    == "y"
):
    print("Updating application code to disable SSL verification...")

    # Create a backup of the email_service.py file
    EMAIL_SERVICE_PATH = "./src/reddit_sentiment_analysis/email_service.py"
    if os.path.exists(EMAIL_SERVICE_PATH):
        with open(EMAIL_SERVICE_PATH, "r") as f:
            email_service_code = f.read()

        # Create backup
        with open(f"{EMAIL_SERVICE_PATH}.bak", "w") as f:
            f.write(email_service_code)

        # Update the code to disable SSL verification
        if "context.check_hostname = False" not in email_service_code:
            email_service_code = email_service_code.replace(
                "context = ssl.create_default_context()",
                "context = ssl.create_default_context()\n            # Disable SSL verification due to Hostinger's self-signed certificate\n            context.check_hostname = False\n            context.verify_mode = ssl.CERT_NONE",
            )

            with open(EMAIL_SERVICE_PATH, "w") as f:
                f.write(email_service_code)

            print(
                "✅ Successfully updated email_service.py to disable SSL verification"
            )
            print(f"Backup created at {EMAIL_SERVICE_PATH}.bak")
        else:
            print("SSL verification already disabled in email_service.py")
    else:
        print(f"❌ Could not find {EMAIL_SERVICE_PATH}")
        print(
            "Please manually update the EmailService class to disable SSL verification."
        )
