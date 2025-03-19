#!/usr/bin/env python3
"""
Test script to check if the OpenAI API key is valid.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from openai import OpenAI


def test_openai_api_key():
    """Test that the OpenAI API key is valid."""
    print("=== Testing OpenAI API Key ===")

    # Try all possible .env locations
    possible_paths = [
        Path(__file__).parent.parent / ".env",  # app/.env
        Path(__file__).parent.parent.parent / ".env",  # .env in root
        Path(__file__).parent.parent.parent / "app" / ".env",  # app/.env from root
    ]

    env_loaded = False
    for env_path in possible_paths:
        if env_path.exists():
            print(f"Loading environment from: {env_path}")
            # Using direct file loading to ensure variables are properly set
            with open(env_path, "r") as file:
                for line in file:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value
                        if key == "OPENAI_API_KEY":
                            print(f"Found OPENAI_API_KEY in {env_path}")
            env_loaded = True
            break

    if not env_loaded:
        print("No .env file found. Using existing environment variables.")

    # Get the API key
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        print("❌ No OpenAI API key found in environment variables.")
        return False

    # Create an obfuscated version of the key for display
    obfuscated_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "****"
    print(f"Found API key: {obfuscated_key}")

    # Test the API key
    try:
        print("Testing API key...")
        client = OpenAI(api_key=api_key)

        # Make a simple API call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, are you working?"}],
            max_tokens=10,
        )

        if response and hasattr(response, "choices") and len(response.choices) > 0:
            print(
                f"✅ API key is valid! Response: {response.choices[0].message.content}"
            )
            return True
        else:
            print(f"❌ API call returned unexpected response: {response}")
            return False

    except Exception as e:
        print(f"❌ API call failed: {str(e)}")
        print("The API key appears to be invalid or there may be connectivity issues.")
        return False


if __name__ == "__main__":
    success = test_openai_api_key()
    print(f"\nTest {'passed' if success else 'failed'}")
    sys.exit(0 if success else 1)
