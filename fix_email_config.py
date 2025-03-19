#!/usr/bin/env python
"""
Script to update email configuration in the .env file.
"""

import getpass
import os
import sys

from dotenv import find_dotenv, load_dotenv, set_key


def main():
    # Find and load the .env file
    dotenv_path = find_dotenv()

    if not dotenv_path:
        print("Error: .env file not found")
        return False

    print(f"Found .env file at: {dotenv_path}")
    load_dotenv(dotenv_path)

    # Get current settings
    current_smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    current_smtp_port = os.getenv("SMTP_PORT", "587")
    current_sender_email = os.getenv("SENDER_EMAIL", "")
    current_password = os.getenv("SENDER_EMAIL_PASSWORD", "")

    # Check if password is a placeholder
    placeholder_detected = current_password in [
        "your_password_here",
        "your_password",
        "password",
        "yourpassword",
    ]

    print("\nCurrent Email Configuration:")
    print(f"SMTP Server: {current_smtp_server}")
    print(f"SMTP Port: {current_smtp_port}")
    print(f"Sender Email: {current_sender_email}")
    if placeholder_detected:
        print("Password: [placeholder detected - needs to be updated]")
    else:
        print("Password: [set - not displayed]")

    # Ask for confirmation
    print("\nWould you like to update these settings? (y/n)")
    if input().lower() != "y":
        print("No changes made.")
        return False

    # Get new values
    smtp_server = input(f"SMTP Server [{current_smtp_server}]: ") or current_smtp_server
    smtp_port = input(f"SMTP Port [{current_smtp_port}]: ") or current_smtp_port
    sender_email = (
        input(f"Sender Email [{current_sender_email}]: ") or current_sender_email
    )

    # Use getpass for the password to hide input
    print("Email Password (input will be hidden): ")
    password = getpass.getpass()

    if not password:
        print("Password cannot be empty.")
        return False

    # Update .env file
    set_key(dotenv_path, "SMTP_SERVER", smtp_server)
    set_key(dotenv_path, "SMTP_PORT", smtp_port)
    set_key(dotenv_path, "SENDER_EMAIL", sender_email)
    set_key(dotenv_path, "SENDER_EMAIL_PASSWORD", password)

    print("\nEmail configuration updated successfully!")
    print("Please restart the application for the changes to take effect.")
    return True


if __name__ == "__main__":
    try:
        success = main()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
