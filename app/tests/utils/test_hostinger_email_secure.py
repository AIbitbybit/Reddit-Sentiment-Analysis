#!/usr/bin/env python
"""
Secure Hostinger Email Test Script
This script tests sending an email using Hostinger SMTP settings with proper SSL certificate handling.
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
print("SECURE HOSTINGER EMAIL TEST".center(60))
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

# Ask if user wants to try installing certifi
try:
    import certifi

    print(
        f"\n✅ certifi is installed. Using certificate bundle from: {certifi.where()}"
    )
    USE_CERTIFI = True
except ImportError:
    print("\n⚠️ certifi package is not installed.")
    print("This package can help with SSL certificate validation.")
    print("Would you like to try installing it now? (y/n):")
    if input("> ").lower() == "y":
        print("Installing certifi package...")
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "certifi"])
        try:
            import certifi

            print(
                f"✅ certifi installed successfully. Using certificate bundle from: {certifi.where()}"
            )
            USE_CERTIFI = True
        except ImportError:
            print("❌ Failed to install certifi. Continuing with default certificates.")
            USE_CERTIFI = False
    else:
        print("Continuing with default certificates.")
        USE_CERTIFI = False

# Confirm before proceeding
print("\nProceed with test? (y/n):")
if input("> ").lower() != "y":
    print("Test cancelled.")
    sys.exit(0)

# Create test email
msg = MIMEMultipart()
msg["Subject"] = "Secure Hostinger Email Test - Reddit Sentiment Analysis"
msg["From"] = SENDER_EMAIL
msg["To"] = TEST_RECIPIENT

# Email body
body = f"""
<html>
<body>
    <h2>Secure Hostinger Email Test</h2>
    <p>This is a test email from the Reddit Sentiment Analysis application.</p>
    <p>If you're seeing this, email sending with Hostinger is working correctly!</p>
    <p><strong>Settings used:</strong></p>
    <ul>
        <li>SMTP Server: {SMTP_SERVER}</li>
        <li>SMTP Port: {SMTP_PORT}</li>
        <li>Sender Email: {SENDER_EMAIL}</li>
        <li>Using certifi: {USE_CERTIFI}</li>
    </ul>
    <p>Timestamp: {time.ctime()}</p>
</body>
</html>
"""

msg.attach(MIMEText(body, "html"))

# Test sending email
print("\n=== Testing Email Sending ===")
print(f"Connecting to {SMTP_SERVER}:{SMTP_PORT}...")

try:
    # Create SSL context with proper certificate handling
    if USE_CERTIFI:
        print("Creating SSL context with certifi certificate bundle")
        context = ssl.create_default_context(cafile=certifi.where())
    else:
        print("Creating default SSL context")
        context = ssl.create_default_context()

    # Function to try different connection methods
    def try_connection_methods():
        # Method 1: SSL on port 465
        try:
            print("\nMethod 1: SSL on port 465")
            with smtplib.SMTP_SSL(SMTP_SERVER, 465, context=context) as server:
                if DEBUG_MODE:
                    server.set_debuglevel(1)

                print(f"Authenticating as {SENDER_EMAIL}...")
                server.login(SENDER_EMAIL, SENDER_PASSWORD)

                print(f"Sending test email to {TEST_RECIPIENT}...")
                server.send_message(msg)
                return True
        except Exception as e:
            print(f"Method 1 failed: {str(e)}")

        # Method 2: STARTTLS on port 587
        try:
            print("\nMethod 2: STARTTLS on port 587")
            with smtplib.SMTP(SMTP_SERVER, 587) as server:
                if DEBUG_MODE:
                    server.set_debuglevel(1)

                server.starttls(context=context)

                print(f"Authenticating as {SENDER_EMAIL}...")
                server.login(SENDER_EMAIL, SENDER_PASSWORD)

                print(f"Sending test email to {TEST_RECIPIENT}...")
                server.send_message(msg)
                return True
        except Exception as e:
            print(f"Method 2 failed: {str(e)}")

        # If both methods fail, return False
        return False

    if try_connection_methods():
        print("\n✅ SUCCESS: Email sent successfully!")
        print(f"Please check {TEST_RECIPIENT} inbox for the test email.")
    else:
        print("\n❌ All connection methods failed.")
        print("Please check the error messages above for more information.")

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback

    print("\nDetailed error information:")
    traceback.print_exc()

    print("\nTroubleshooting suggestions:")
    print("1. Check if your email provider supports other ports (587 for STARTTLS)")
    print("2. Verify your email credentials")
    print("3. Check if your email provider requires any special configuration")
    print("4. Try using a different email provider for testing")

print("\n" + "=" * 60)
print("TEST COMPLETED".center(60))
print("=" * 60)
