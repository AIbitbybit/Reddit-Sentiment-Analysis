#!/usr/bin/env python
"""
Script to check the actual content of the .env file
"""

import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv


def main():
    # Find the .env file
    dotenv_path = find_dotenv()

    if not dotenv_path:
        print("Error: .env file not found")
        return

    print(f"Found .env file at: {dotenv_path}")

    # Load it with dotenv
    load_dotenv(dotenv_path)

    # Print the values from environment after loading
    print("\nValues from environment after loading dotenv:")
    print(f"SMTP_SERVER: {os.getenv('SMTP_SERVER')}")
    print(f"SMTP_PORT: {os.getenv('SMTP_PORT')}")
    print(f"SENDER_EMAIL: {os.getenv('SENDER_EMAIL')}")
    print(
        f"SENDER_EMAIL_PASSWORD: {'[SET]' if os.getenv('SENDER_EMAIL_PASSWORD') else '[NOT SET]'}"
    )
    if os.getenv("SENDER_EMAIL_PASSWORD") == "your_password_here":
        print("Warning: Password is still set to 'your_password_here'")

    # Now read the file directly to see what's actually in it
    print("\nDirect read of .env file content:")
    try:
        with open(dotenv_path, "r") as f:
            lines = f.readlines()

        # Display each line, masking actual passwords
        for line in lines:
            if line.strip() and not line.startswith("#"):
                if "PASSWORD" in line.upper():
                    key, value = line.strip().split("=", 1)
                    if value:
                        # Mask the actual password
                        print(f"{key}=[PASSWORD VALUE MASKED]")
                    else:
                        print(f"{key}=[EMPTY]")
                else:
                    print(line.strip())

        # Check specific password placeholder issue
        password_line = next(
            (line for line in lines if "SENDER_EMAIL_PASSWORD" in line), None
        )
        if password_line:
            key, value = password_line.strip().split("=", 1)
            if value == "your_password_here":
                print(
                    "\nIssue detected: Email password is set to 'your_password_here' in .env file"
                )
            elif not value:
                print("\nIssue detected: Email password is empty in .env file")
            else:
                value_length = len(value)
                print(
                    f"\nEmail password appears to be set (length: {value_length} characters)"
                )
        else:
            print("\nIssue detected: SENDER_EMAIL_PASSWORD line not found in .env file")
    except Exception as e:
        print(f"Error reading .env file directly: {str(e)}")

    # Check where the dotenv file is being loaded from in the app
    app_root = Path(__file__).parent
    app_src_dir = app_root / "app" / "src" / "reddit_sentiment_analysis"

    print("\nSearching for dotenv loading in the application:")
    dotenv_loads = []

    for root, dirs, files in os.walk(app_src_dir):
        for file in files:
            if file.endswith(".py"):
                try:
                    path = os.path.join(root, file)
                    with open(path, "r") as f:
                        content = f.read()
                        if "load_dotenv" in content:
                            dotenv_loads.append(path)
                except:
                    pass

    print(f"Found {len(dotenv_loads)} files with dotenv loading:")
    for file in dotenv_loads:
        print(f"- {os.path.relpath(file, app_root)}")


if __name__ == "__main__":
    main()
