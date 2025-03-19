#!/usr/bin/env python
"""
Email debugging script to test SMTP connection and sending.
This script provides more detailed error information to troubleshoot email issues.
"""

import os
import smtplib
import ssl
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_EMAIL_PASSWORD")
TEST_RECIPIENT = "test@example.com"  # Replace with your test email


def print_config():
    """Print the current email configuration."""
    print("\n=== Email Configuration ===")
    print(f"SMTP Server: {SMTP_SERVER}")
    print(f"SMTP Port: {SMTP_PORT}")
    print(f"Sender Email: {SENDER_EMAIL}")
    print(f"Password: {'*' * 8 if SENDER_PASSWORD else 'Not set'}")


def test_smtp_connection():
    """Test the SMTP connection without sending an email."""
    print("\n=== Testing SMTP Connection ===")

    if not all([SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD]):
        print("❌ Error: Missing email configuration. Check your .env file.")
        return False

    try:
        print(f"Connecting to {SMTP_SERVER}:{SMTP_PORT}...")

        # Try different connection methods
        success = False

        # Method 1: Basic connection
        try:
            print("\nMethod 1: Basic SMTP connection")
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            server.set_debuglevel(1)  # Enable debug output
            print("Connected to SMTP server")
            server.quit()
            success = True
            print("✓ Basic connection successful")
        except Exception as e:
            print(f"✗ Basic connection failed: {str(e)}")

        # Method 2: SSL Connection
        try:
            print("\nMethod 2: SSL Connection")
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(
                SMTP_SERVER, SMTP_PORT, timeout=10, context=context
            )
            server.set_debuglevel(1)  # Enable debug output
            print("Connected to SMTP server using SSL")
            server.quit()
            success = True
            print("✓ SSL connection successful")
        except Exception as e:
            print(f"✗ SSL connection failed: {str(e)}")

        # Method 3: STARTTLS Connection
        try:
            print("\nMethod 3: STARTTLS Connection")
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            server.set_debuglevel(1)  # Enable debug output
            server.starttls(context=ssl.create_default_context())
            print("Started TLS")
            server.quit()
            success = True
            print("✓ STARTTLS connection successful")
        except Exception as e:
            print(f"✗ STARTTLS connection failed: {str(e)}")

        if success:
            print("\n✅ Successfully connected to SMTP server with at least one method")
            return True
        else:
            print("\n❌ All connection methods failed")
            print("Common issues:")
            print("1. Incorrect SMTP server or port")
            print("2. Firewall or network restrictions")
            print("3. Server requires authentication to connect")
            return False

    except Exception as e:
        print(f"❌ Error connecting to SMTP server: {str(e)}")
        return False


def test_authentication():
    """Test authentication with the SMTP server."""
    print("\n=== Testing SMTP Authentication ===")

    if not all([SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD]):
        print("❌ Error: Missing email configuration. Check your .env file.")
        return False

    try:
        # Determine connection method based on port
        use_ssl = SMTP_PORT == 465

        print(f"Using {'SSL' if use_ssl else 'STARTTLS'} connection method")

        if use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(
                SMTP_SERVER, SMTP_PORT, timeout=15, context=context
            )
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
            server.starttls(context=ssl.create_default_context())

        server.set_debuglevel(1)  # Enable debug output

        # Try to login
        print(f"Authenticating as {SENDER_EMAIL}...")
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        print("✅ Authentication successful")
        server.quit()
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {str(e)}")
        print("\nCommon authentication issues:")
        print("1. Incorrect password")
        print("2. Two-factor authentication is enabled (use app password instead)")
        print("3. Account security settings blocking 'less secure apps'")
        print("4. Captcha or verification required after too many failed attempts")
        return False

    except Exception as e:
        print(f"❌ Error during authentication: {str(e)}")
        return False


def test_send_email():
    """Test sending an email."""
    print("\n=== Testing Email Sending ===")

    if not all([SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD]):
        print("❌ Error: Missing email configuration. Check your .env file.")
        return False

    # Create test email
    msg = MIMEMultipart()
    msg["Subject"] = "Test Email from Reddit Sentiment Analysis"
    msg["From"] = SENDER_EMAIL
    msg["To"] = TEST_RECIPIENT

    body = """
    <html>
    <body>
        <h2>Test Email</h2>
        <p>This is a test email from the Reddit Sentiment Analysis application.</p>
        <p>If you're seeing this, email sending is working correctly!</p>
        <p>Timestamp: {}</p>
    </body>
    </html>
    """.format(
        time.ctime()
    )

    msg.attach(MIMEText(body, "html"))

    try:
        # Determine connection method based on port
        use_ssl = SMTP_PORT == 465

        print(f"Using {'SSL' if use_ssl else 'STARTTLS'} connection method")

        if use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(
                SMTP_SERVER, SMTP_PORT, timeout=15, context=context
            )
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
            server.starttls(context=ssl.create_default_context())

        server.set_debuglevel(1)  # Enable debug output

        # Login and send
        print(f"Authenticating as {SENDER_EMAIL}...")
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        print(f"Sending email to {TEST_RECIPIENT}...")
        server.send_message(msg)
        print("✅ Email sent successfully")
        server.quit()
        return True

    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        return False


def suggest_fixes():
    """Suggest potential fixes based on email provider."""
    print("\n=== Troubleshooting Suggestions ===")

    if "hostinger" in SMTP_SERVER.lower():
        print("Hostinger Email Suggestions:")
        print("1. Verify your SMTP server: smtp.hostinger.com")
        print("2. Try using port 587 with STARTTLS instead of port 465 with SSL")
        print("3. Check if your Hostinger email has restrictions on sending")
        print("4. Ensure you're using the full email address for login")
        print("5. Check Hostinger's control panel for any sending limitations")

    elif "gmail" in SMTP_SERVER.lower():
        print("Gmail Suggestions:")
        print(
            "1. Use an App Password instead of your regular password: https://support.google.com/accounts/answer/185833"
        )
        print(
            "2. Make sure 'Less secure app access' is turned on (for older Gmail accounts)"
        )
        print("3. Check if you've exceeded sending limits")
        print("4. Try using port 587 (STARTTLS) instead of 465 (SSL)")

    elif "outlook" in SMTP_SERVER.lower() or "hotmail" in SMTP_SERVER.lower():
        print("Outlook/Hotmail Suggestions:")
        print("1. Verify SMTP server: smtp.office365.com")
        print("2. Use port 587 with STARTTLS")
        print("3. Check for account sending restrictions")

    print("\nGeneral Suggestions:")
    print("1. Check if your email provider's server is down")
    print("2. Verify network connectivity (no firewall blocking SMTP ports)")
    print("3. Try a different email provider for testing")
    print("4. Check if your provider requires specific SSL/TLS configurations")


def main():
    """Main function to run all tests."""
    print("\n" + "=" * 60)
    print("EMAIL CONFIGURATION TESTING TOOL".center(60))
    print("=" * 60)

    print_config()

    tests = [
        ("SMTP Connection", test_smtp_connection),
        ("SMTP Authentication", test_authentication),
        ("Email Sending", test_send_email),
    ]

    results = {}
    for name, test_func in tests:
        print("\n" + "=" * 60)
        result = test_func()
        results[name] = result

    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY".center(60))
    print("=" * 60)

    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name}: {status}")

    if not all(results.values()):
        suggest_fixes()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

    # Ask to update settings
    if any(not result for result in [test_smtp_connection(), test_authentication()]):
        print("\nWould you like to update your email settings? (y/n)")
        response = input("> ").strip().lower()

        if response == "y":
            print("\nEnter new SMTP server (or press Enter to keep current):")
            new_server = input(f"[{SMTP_SERVER}] > ").strip() or SMTP_SERVER

            print("\nEnter new SMTP port (or press Enter to keep current):")
            new_port_str = input(f"[{SMTP_PORT}] > ").strip() or str(SMTP_PORT)
            new_port = int(new_port_str)

            print("\nEnter new sender email (or press Enter to keep current):")
            new_email = input(f"[{SENDER_EMAIL}] > ").strip() or SENDER_EMAIL

            print("\nEnter new password (or press Enter to keep current):")
            new_password = input("Password > ").strip() or SENDER_PASSWORD

            # Update .env file
            env_file = ".env"
            with open(env_file, "r") as f:
                env_lines = f.readlines()

            updated_lines = []
            for line in env_lines:
                if line.startswith("SMTP_SERVER="):
                    updated_lines.append(f"SMTP_SERVER={new_server}\n")
                elif line.startswith("SMTP_PORT="):
                    updated_lines.append(f"SMTP_PORT={new_port}\n")
                elif line.startswith("SENDER_EMAIL="):
                    updated_lines.append(f"SENDER_EMAIL={new_email}\n")
                elif line.startswith("SENDER_EMAIL_PASSWORD="):
                    updated_lines.append(f"SENDER_EMAIL_PASSWORD={new_password}\n")
                else:
                    updated_lines.append(line)

            with open(env_file, "w") as f:
                f.writelines(updated_lines)

            print(
                "\n✅ Settings updated. Please restart the application to apply changes."
            )
        else:
            print("\nSettings not updated. You can manually edit the .env file.")
