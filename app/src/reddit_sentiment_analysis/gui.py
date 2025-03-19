"""
GUI for the Reddit Sentiment Analysis application.
Provides a user interface for monitoring Reddit comments about specific key terms.
"""

import asyncio
import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st
from dotenv import find_dotenv, load_dotenv
from openai import OpenAI
from reddit_sentiment_analysis.config import DEFAULT_SUBREDDITS
from reddit_sentiment_analysis.data_collection.collector import DataCollector
from reddit_sentiment_analysis.data_collection.reddit_client import (
    TOKEN_PATH,
    RedditClient,
)
from reddit_sentiment_analysis.email_service import EmailService
from reddit_sentiment_analysis.monitoring import RedditMonitor
from reddit_sentiment_analysis.storage.comment_db import CommentDatabase

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Create a custom handler for GUI logs
class GUILogHandler(logging.Handler):
    """Custom logging handler that stores logs for display in the GUI."""

    def __init__(self):
        super().__init__()
        self.logs = []
        self.max_logs = 100  # Maximum number of logs to keep

    def emit(self, record):
        """Process a log record and store it."""
        log_entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "level": record.levelname,
            "message": self.format(record),
        }

        # Only store important logs for the GUI
        if self._is_important_log(record):
            self.logs.append(log_entry)

            # Trim logs if they exceed the maximum
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs :]

    def _is_important_log(self, record):
        """Determine if a log is important enough to show in the GUI."""
        # Filter out debug logs
        if record.levelno < logging.INFO:
            return False

        # Include all error and critical logs
        if record.levelno >= logging.ERROR:
            return True

        # Filter for specific important messages
        msg = record.getMessage().lower()
        important_keywords = [
            "monitoring",
            "found",
            "comment",
            "scan",
            "sentiment",
            "negative",
            "email",
            "alert",
            "response",
            "reddit",
            "post",
        ]

        # Check if the message contains any important keywords
        return any(keyword in msg for keyword in important_keywords)

    def get_logs(self):
        """Get the stored logs."""
        return self.logs

    def clear(self):
        """Clear all stored logs."""
        self.logs = []


# Create and add the GUI log handler
gui_log_handler = GUILogHandler()
gui_log_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(gui_log_handler)

# Global variables
monitor_thread = None
# The global stop_monitoring flag will be synced with session state
stop_monitoring = False
# Dictionary to track all monitoring threads
monitoring_threads = {}
# Current monitoring session ID
current_monitoring_id = None

# Load environment variables
load_dotenv()


def get_default_settings():
    """Get default settings from environment variables.
    This is designed to be called each time we need the defaults,
    so we always get the latest values from the environment."""

    # Load environment variables first
    env_path = find_dotenv()
    if env_path:
        load_dotenv(dotenv_path=env_path, override=True)
        logger.info(f"Loaded environment variables from {env_path}")

    return {
        "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": os.getenv("SMTP_PORT", "587"),
        "sender_email": os.getenv("SENDER_EMAIL", ""),
        "sender_email_password": os.getenv("SENDER_EMAIL_PASSWORD", ""),
        "reddit_client_id": os.getenv("REDDIT_CLIENT_ID", ""),
        "reddit_client_secret": os.getenv("REDDIT_CLIENT_SECRET", ""),
        "reddit_user_agent": os.getenv(
            "REDDIT_USER_AGENT", "python:reddit-sentiment-analysis:v0.1.0"
        ),
        "reddit_username": os.getenv("REDDIT_USERNAME", ""),
        "reddit_password": os.getenv("REDDIT_PASSWORD", ""),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o"),
        "check_interval": os.getenv("CHECK_INTERVAL", "300"),
    }


# Replace the static DEFAULT_SETTINGS with a function call
# Load environment variables
load_dotenv()

# Default settings will be obtained when needed
DEFAULT_SETTINGS = get_default_settings()

# Create a lock file path to track monitoring state
MONITOR_LOCK_FILE = (
    Path(__file__).parent.parent.parent.absolute() / "monitor_state.json"
)


def save_settings(settings):
    """Save settings to .env file."""
    try:
        # List of known placeholder texts for sensitive fields
        placeholders = [
            "your_password_here",
            "your_password",
            "password",
            "yourpassword",
        ]

        # Find the user's .env file
        env_file = find_dotenv()
        if not env_file:
            # Create a new .env file in the app directory
            env_file = Path(__file__).parent.parent.parent.parent / ".env"
            logger.info(f"Creating new .env file at {env_file}")
        else:
            logger.info(f"Updating existing .env file at {env_file}")

        # Load current environment variables to keep any that aren't in our settings
        current_env = {}
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        current_env[key] = value

        # Sensitive settings that shouldn't be overwritten with empty values
        sensitive_keys = [
            "OPENAI_API_KEY",
            "SENDER_EMAIL_PASSWORD",
            "REDDIT_CLIENT_SECRET",
        ]

        # Write settings to .env file
        with open(env_file, "w") as f:
            for key, value in settings.items():
                env_key = key.upper()

                # Handle sensitive settings specially
                if env_key in sensitive_keys:
                    # Skip if value is empty or looks like a placeholder
                    if not value or any(
                        placeholder.lower() in value.lower()
                        for placeholder in placeholders
                    ):
                        # Keep the existing value if we have one
                        if env_key in current_env and current_env[env_key]:
                            logger.info(f"Keeping existing value for {env_key}")
                            f.write(f"{env_key}={current_env[env_key]}\n")
                    else:
                        # Write the new value
                        f.write(f"{env_key}={value}\n")
                # For non-sensitive settings, only write non-empty values
                elif value:
                    f.write(f"{env_key}={value}\n")
                # Preserve existing non-sensitive settings if not in our settings dictionary
                else:
                    if env_key in current_env and current_env[env_key]:
                        f.write(f"{env_key}={current_env[env_key]}\n")

        # Reload environment variables
        load_dotenv(dotenv_path=env_file, override=True)

        # Set environment variables explicitly to ensure they're available to all parts of the app
        for key, value in settings.items():
            env_key = key.upper()
            # For sensitive keys, don't override if the value is empty or a placeholder
            if env_key in sensitive_keys:
                if not value or any(
                    placeholder.lower() in value.lower() for placeholder in placeholders
                ):
                    # Keep the existing environment variable
                    continue
            # Set the environment variable if non-empty
            if value:
                os.environ[env_key] = value

        return True
    except Exception as e:
        logger.error(f"Error saving settings: {str(e)}")
        return False


def load_settings():
    """Load settings from .env file."""
    # Always get fresh defaults from environment to ensure we have the latest values
    settings = get_default_settings()

    # Special handling for sensitive values
    sensitive_keys = ["openai_api_key", "sender_email_password", "reddit_client_secret"]

    # List of known placeholders to ignore
    placeholders = [
        "your_password_here",
        "your_password",
        "password",
        "yourpassword",
        "your-key-here",
        "your_client_secret_here",
        "your-api-key-here",
    ]

    # Log the loaded values for debugging
    for key in sensitive_keys:
        env_key = key.upper()
        env_value = os.getenv(env_key)

        if env_value:
            if any(
                placeholder.lower() in env_value.lower() for placeholder in placeholders
            ):
                logger.warning(f"Detected placeholder value for {env_key}")
            else:
                logger.info(f"Loaded {env_key} with value of length: {len(env_value)}")
        else:
            logger.warning(f"No value found for {env_key}")

    # Extra check - directly read the .env file for debugging
    env_path = find_dotenv()
    if env_path:
        try:
            with open(env_path, "r") as f:
                env_content = f.read()

            # Check if each sensitive key exists in the file
            for key in sensitive_keys:
                env_key = key.upper()
                if f"{env_key}=" in env_content:
                    # Find the line containing this key
                    lines = env_content.splitlines()
                    for line in lines:
                        if line.startswith(f"{env_key}="):
                            value = line.split("=", 1)[1].strip() if "=" in line else ""
                            if value:
                                # Don't log the actual value, just whether it exists and isn't a placeholder
                                if any(
                                    placeholder.lower() in value.lower()
                                    for placeholder in placeholders
                                ):
                                    logger.warning(
                                        f"Found placeholder value for {env_key} in .env file"
                                    )
                                else:
                                    logger.info(
                                        f"Found non-placeholder value for {env_key} in .env file (length: {len(value)})"
                                    )

                                    # Make sure it's set in our settings dict
                                    settings[key.lower()] = value
                            else:
                                logger.warning(
                                    f"Found empty value for {env_key} in .env file"
                                )
                else:
                    logger.warning(f"Key {env_key} not found in .env file")
        except Exception as e:
            logger.warning(f"Error reading .env file directly: {e}")

    return settings


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def save_monitor_state(
    active=True, key_term="", email="", subreddits=None, start_time=None
):
    """Save monitoring state to a file to persist across refreshes."""
    if subreddits is None:
        subreddits = []

    # Get the current check interval
    try:
        check_interval = int(os.getenv("CHECK_INTERVAL", "300"))
    except ValueError:
        check_interval = 300

    state = {
        "active": active,
        "key_term": key_term,
        "email": email,
        "subreddits": subreddits,
        "start_time": start_time.isoformat() if start_time else None,
        "check_interval": check_interval,
    }

    try:
        with open(MONITOR_LOCK_FILE, "w") as f:
            json.dump(state, f)
        logger.info(f"Saved monitoring state: {state}")
    except Exception as e:
        logger.error(f"Error saving monitoring state: {e}")


def load_monitor_state():
    """Load monitoring state from file."""
    if not MONITOR_LOCK_FILE.exists():
        return None

    try:
        with open(MONITOR_LOCK_FILE, "r") as f:
            state = json.load(f)

        # Convert start_time back to datetime
        if state.get("start_time"):
            state["start_time"] = datetime.fromisoformat(state["start_time"])

        logger.info(f"Loaded monitoring state: {state}")
        return state
    except Exception as e:
        logger.error(f"Error loading monitoring state: {e}")
        return None


def safe_update_session_state(updates: dict):
    """
    Safely update Streamlit session state without triggering ScriptRunContext warnings.

    Args:
        updates: Dictionary of key-value pairs to update in session state
    """
    # Only update if we're in the main thread
    if not threading.current_thread() is threading.main_thread():
        return

    # Only update if st.session_state is available
    if not hasattr(st, "session_state"):
        return

    try:
        for key, value in updates.items():
            if key in st.session_state or value is not None:
                st.session_state[key] = value
    except:
        # Silently fail if we can't update session state
        pass


def start_monitoring(
    key_term: str, email: str, subreddits: List[str], db: CommentDatabase
):
    """Start monitoring Reddit in a separate thread."""
    global monitor_thread, stop_monitoring, monitoring_threads, current_monitoring_id

    # Stop any existing monitoring threads
    stop_all_monitoring_threads()

    # Initialize session state for monitoring status if not exists
    if "monitoring_active" not in st.session_state:
        st.session_state.monitoring_active = False
    if "last_refresh_time" not in st.session_state:
        st.session_state.last_refresh_time = datetime.now()
    if "stop_monitoring_flag" not in st.session_state:
        st.session_state.stop_monitoring_flag = False

    # Reset stopping flags - important to clear this first
    st.session_state.stop_monitoring_flag = False
    stop_monitoring = False

    # Set monitoring as active
    st.session_state.monitoring_active = True
    start_time = datetime.now()
    st.session_state.monitoring_start_time = start_time
    st.session_state.key_term = key_term
    st.session_state.monitored_subreddits = subreddits
    st.session_state.monitor_email = email
    st.session_state.last_refresh_time = datetime.now()

    # Store current check interval in session state
    try:
        check_interval = int(os.getenv("CHECK_INTERVAL", "300"))
    except ValueError:
        check_interval = 300
    st.session_state.check_interval = check_interval

    # Generate a unique ID for this monitoring session
    session_id = f"monitor_{int(time.time())}"
    current_monitoring_id = session_id

    # Save state to file for persistence across refreshes
    save_monitor_state(
        active=True,
        key_term=key_term,
        email=email,
        subreddits=subreddits,
        start_time=start_time,
    )

    # Create a new monitor and thread
    monitor = RedditMonitor(key_term, email, subreddits, db)
    monitor_thread = threading.Thread(
        target=run_monitor_loop, args=(monitor, session_id)
    )
    monitor_thread.daemon = True

    # Store in registry
    monitoring_threads[session_id] = {
        "thread": monitor_thread,
        "key_term": key_term,
        "subreddits": subreddits,
        "start_time": start_time,
        "active": True,
    }

    # Start the thread
    logger.info(f"Starting monitoring thread {session_id} for key term '{key_term}'")
    monitor_thread.start()

    # Force a rerun to update the UI immediately
    try:
        st.rerun()
    except:
        pass

    return True


def stop_all_monitoring_threads():
    """Stop all monitoring threads aggressively."""
    global stop_monitoring, monitoring_threads, current_monitoring_id

    if not monitoring_threads:
        return

    logger.info(f"Stopping all monitoring threads: {list(monitoring_threads.keys())}")

    # Set the global stop flag
    stop_monitoring = True

    # Try to terminate all threads immediately
    thread_count = 0
    for session_id, thread_info in list(monitoring_threads.items()):
        thread = thread_info.get("thread")
        if thread and thread.is_alive():
            thread_count += 1
            logger.info(f"Joining thread {session_id} with a 5-second timeout")
            thread.join(timeout=5)
            if thread.is_alive():
                logger.warning(
                    f"Thread {session_id} did not terminate within the timeout"
                )
            else:
                logger.info(f"Thread {session_id} terminated successfully")

    # Log how many threads were attempted to stop
    if thread_count > 0:
        logger.info(f"Forcefully stopped {thread_count} active threads")

    # Mark all threads as inactive to ensure the UI updates correctly
    for session_id in list(monitoring_threads.keys()):
        monitoring_threads[session_id]["active"] = False

    # Reset session ID
    current_monitoring_id = None


def run_monitor_loop(monitor: RedditMonitor, session_id: str = None):
    """Run the monitoring loop."""
    global stop_monitoring, current_monitoring_id, monitoring_threads

    # Get check interval from settings (default to 300 seconds / 5 minutes)
    try:
        check_interval = int(os.getenv("CHECK_INTERVAL", "300"))
    except ValueError:
        check_interval = 300

    # Log start of monitoring loop
    logger.info(
        f"Monitor loop started for session {session_id} with key term '{monitor.key_term}'"
    )

    while True:
        # First check if we should stop
        if stop_monitoring:
            logger.info("Global stop flag detected, terminating monitor loop")
            break

        # Check if this monitor session is still current
        if session_id and current_monitoring_id != session_id:
            logger.info(
                f"Terminating outdated monitoring session {session_id} (current is {current_monitoring_id})"
            )
            break

        try:
            # Log the scan start
            logger.info(
                f"Starting scan for comments containing '{monitor.key_term}' in {', '.join(monitor.subreddits)}"
            )

            # Use asyncio to run the async monitor method
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(monitor.check_for_new_comments())
            loop.close()

            # Log the scan results
            if results:
                logger.info(
                    f"Found {len(results)} new comments matching '{monitor.key_term}'"
                )
            else:
                logger.info(f"No new comments found matching '{monitor.key_term}'")

            # Wait before next check using small intervals to allow for faster stopping
            logger.info(f"Waiting {check_interval} seconds until next scan")

            # Use short sleep intervals (1 second) to be more responsive to stop requests
            for _ in range(check_interval):
                if stop_monitoring:
                    logger.info("Stop flag detected during sleep, terminating loop")
                    break
                time.sleep(1)  # Sleep for 1 second at a time

            # Check stop flag again after sleep
            if stop_monitoring:
                logger.info("Stop flag detected after sleep, terminating loop")
                break

        except Exception as e:
            logger.error(f"Error in monitoring thread {session_id}: {str(e)}")
            # Wait a bit after an error before retrying
            time.sleep(5)

            # Check stop flag again after error
            if stop_monitoring:
                logger.info("Stop flag detected after error, terminating loop")
                break

    # Thread is stopping - update registry
    if session_id and session_id in monitoring_threads:
        monitoring_threads[session_id]["active"] = False

    # Log monitoring stopped
    logger.info(f"Monitoring session {session_id} stopped")


def format_duration(duration):
    """Format a timedelta into a user-friendly string.

    Examples:
        - "Just started" for durations less than 1 minute
        - "1 minute" for 1 minute
        - "5 minutes" for 5 minutes
        - "1 hour, 5 minutes" for that duration
        - "2 hours" for exactly 2 hours
        - "1 day, 3 hours" for that duration
    """
    # Calculate total days, including the .days attribute
    total_seconds = int(duration.total_seconds())

    # Handle edge cases
    if total_seconds < 60:
        return "Just started"

    # Calculate days, hours, minutes
    days, remainder = divmod(total_seconds, 86400)  # 86400 seconds in a day
    hours, remainder = divmod(remainder, 3600)  # 3600 seconds in an hour
    minutes, _ = divmod(remainder, 60)  # 60 seconds in a minute

    # Format the duration based on its length
    parts = []
    if days > 0:
        parts.append(f"{days} {'day' if days == 1 else 'days'}")
    if hours > 0:
        parts.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
    if minutes > 0 and days == 0:  # Only show minutes if less than a day
        parts.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")

    # If we have days but no hours, and some minutes, include the minutes
    if days > 0 and hours == 0 and minutes > 0:
        parts.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")

    # Make sure we return something even if all parts are zero
    if not parts:
        return "Just started"

    # Join the parts with commas
    return ", ".join(parts)


def display_monitoring_status():
    """Display the current monitoring status with reliable controls."""
    # Initialize session state variables if they don't exist
    if "monitoring_active" not in st.session_state:
        st.session_state.monitoring_active = False
    if "monitoring_start_time" not in st.session_state:
        st.session_state.monitoring_start_time = None
    if "last_refresh_time" not in st.session_state:
        st.session_state.last_refresh_time = datetime.now()
    if "stop_monitoring_flag" not in st.session_state:
        st.session_state.stop_monitoring_flag = False

    # Create a container for the status display
    status_container = st.container()

    with status_container:
        if st.session_state.monitoring_active:
            # Calculate duration
            current_time = datetime.now()
            duration = current_time - st.session_state.monitoring_start_time
            duration_text = format_duration(duration)

            # Display active monitoring status with green background
            st.success(f"**🔍 MONITORING ACTIVE** - Running for: **{duration_text}**")

            # Create layout for stop button with visual cue
            col1, col2 = st.columns([2, 1])

            # Add text as a visual cue to locate the button
            with col1:
                st.markdown("#### Click the STOP button to end monitoring →")

            # Add a prominent STOP button that directly calls stop_monitoring_process
            with col2:
                if st.button(
                    "⏹️ STOP MONITORING",
                    key="stop_monitoring_main",
                    type="primary",
                    use_container_width=True,
                    help="Click to immediately stop all monitoring activities",
                ):
                    # Call the stop function directly
                    logger.info("Stop button clicked - calling stop_monitoring_process")
                    stop_monitoring_process()
                    st.rerun()  # Add an extra rerun to ensure the UI updates
        else:
            # Display inactive status with light gray background
            st.info("**MONITORING INACTIVE** - Scan is currently stopped")

            # If we have previous monitoring data, show it
            if (
                hasattr(st.session_state, "last_monitoring_duration")
                and st.session_state.last_monitoring_duration
            ):
                duration_text = format_duration(
                    st.session_state.last_monitoring_duration
                )
                st.markdown(f"Last scan duration: {duration_text}")


def settings_ui():
    """Settings UI for configuring the application."""
    st.header("Settings")

    # Load current settings
    settings = load_settings()

    # Store original sensitive settings to avoid replacing with placeholders
    original_sensitive_settings = {
        "sender_email_password": settings.get("sender_email_password", ""),
        "openai_api_key": settings.get("openai_api_key", ""),
        "reddit_client_secret": settings.get("reddit_client_secret", ""),
    }

    # Create tabs for different settings categories
    email_tab, reddit_tab, openai_tab, general_tab = st.tabs(
        ["Email Settings", "Reddit API", "OpenAI API", "General Settings"]
    )

    with email_tab:
        st.subheader("Email Configuration")
        st.info(
            "Configure the email service for sending alerts and processing responses."
        )

        smtp_server = st.text_input(
            "SMTP Server", value=settings["smtp_server"], help="e.g., smtp.gmail.com"
        )
        smtp_port = st.text_input(
            "SMTP Port",
            value=settings["smtp_port"],
            help="e.g., 587 for TLS or 465 for SSL",
        )
        sender_email = st.text_input(
            "Sender Email",
            value=settings["sender_email"],
            help="The email address to send alerts from",
        )

        # Check if a valid password is set
        has_valid_password = (
            settings["sender_email_password"]
            and settings["sender_email_password"] != "your_password_here"
        )

        # Show a status indicator for the password
        if has_valid_password:
            st.success("✅ Email password is configured")
        else:
            st.warning("⚠️ Email password is not set or contains a placeholder")

        # Password field with better placeholder
        password_placeholder = (
            "Leave empty to keep existing password"
            if has_valid_password
            else "No password set - enter a password"
        )

        # Help text for password field
        password_help = (
            "For Gmail, use an App Password: https://myaccount.google.com/apppasswords"
        )
        if has_valid_password:
            password_help = "Password is already set. Enter a new one only if you want to change it."

        sender_password = st.text_input(
            "Email Password/App Password",
            value="",
            type="password",
            placeholder=password_placeholder,
            help=password_help,
        )

        # Only update password if user entered a new one
        settings["smtp_server"] = smtp_server
        settings["smtp_port"] = smtp_port
        settings["sender_email"] = sender_email
        if sender_password:
            settings["sender_email_password"] = sender_password
        else:
            # Keep the original password
            settings["sender_email_password"] = original_sensitive_settings[
                "sender_email_password"
            ]

    with reddit_tab:
        st.subheader("Reddit API Configuration")
        st.info(
            "Configure the Reddit API credentials for reading comments and posting responses."
        )

        # Reddit API settings section
        reddit_client_id = st.text_input(
            "Reddit API Client ID",
            value=settings.get("reddit_client_id", ""),
            help="Client ID from your Reddit app",
            type="default",
        )

        # Check if a valid client secret is set
        has_valid_secret = (
            settings["reddit_client_secret"]
            and settings["reddit_client_secret"] != "your_client_secret_here"
        )

        # Show a status indicator for the client secret
        if has_valid_secret:
            st.success("✅ Reddit client secret is configured")
        else:
            st.warning("⚠️ Reddit client secret is not set or contains a placeholder")

        # Client secret field with better placeholder
        secret_placeholder = (
            "Leave empty to keep existing secret"
            if has_valid_secret
            else "No client secret set - enter a secret"
        )

        # Help text for client secret field
        secret_help = "Client Secret from your Reddit app"
        if has_valid_secret:
            secret_help = "Client secret is already set. Enter a new one only if you want to change it."

        reddit_client_secret = st.text_input(
            "Reddit API Client Secret",
            value="",  # Don't show actual value, even masked
            type="password",
            placeholder=secret_placeholder,
            help=secret_help,
        )

        reddit_user_agent = st.text_input(
            "Reddit API User Agent",
            value=settings.get("reddit_user_agent", ""),
            help="User Agent for Reddit API requests",
            type="default",
        )

        st.markdown("### Reddit Authentication")
        st.markdown(
            """
        Reddit authentication is required to post comments. 
        To authenticate, click the button below and follow the instructions.
        """
        )

        # Create columns for the authentication buttons
        auth_col1, auth_col2 = st.columns(2)

        # Initialize a Reddit client to check if it's authenticated
        try:
            reddit_client = RedditClient()
            if reddit_client.is_authenticated and reddit_client.can_post:
                st.success(f"✅ Authenticated as u/{reddit_client.username}")

                if auth_col1.button(
                    "Re-authenticate (Automatic)", key="reddit_auth_auto"
                ):
                    with st.spinner("Authenticating with Reddit..."):
                        try:
                            if reddit_client.authenticate():
                                st.success(
                                    f"Authentication successful! You are now logged in as u/{reddit_client.username}"
                                )
                                st.rerun()  # Refresh the page to update authentication status
                            else:
                                st.error(
                                    "Authentication failed. Please try the manual method."
                                )
                        except Exception as e:
                            st.error(f"Error during authentication: {str(e)}")

                if auth_col2.button(
                    "Re-authenticate (Manual)", key="reddit_auth_manual"
                ):
                    try:
                        st.info(
                            "Please check the terminal window for authentication instructions."
                        )
                        if reddit_client.authenticate_manual():
                            st.success(
                                f"Authentication successful! You are now logged in as u/{reddit_client.username}"
                            )
                            st.rerun()  # Refresh the page to update authentication status
                        else:
                            st.error(
                                "Authentication failed. Please check the terminal for error messages."
                            )
                    except Exception as e:
                        st.error(f"Error during authentication: {str(e)}")
            else:
                st.warning(
                    "Not authenticated with Reddit. You won't be able to post comments."
                )

                if auth_col1.button("Authenticate (Automatic)", key="reddit_auth_auto"):
                    with st.spinner("Authenticating with Reddit..."):
                        try:
                            if reddit_client.authenticate():
                                st.success(
                                    f"Authentication successful! You are now logged in as u/{reddit_client.username}"
                                )
                                st.rerun()  # Refresh the page to update authentication status
                            else:
                                st.error(
                                    "Authentication failed. Please try the manual method."
                                )
                        except Exception as e:
                            st.error(f"Error during authentication: {str(e)}")

                if auth_col2.button("Authenticate (Manual)", key="reddit_auth_manual"):
                    try:
                        st.info(
                            "Please check the terminal window for authentication instructions."
                        )
                        if reddit_client.authenticate_manual():
                            st.success(
                                f"Authentication successful! You are now logged in as u/{reddit_client.username}"
                            )
                            st.rerun()  # Refresh the page to update authentication status
                        else:
                            st.error(
                                "Authentication failed. Please check the terminal for error messages."
                            )
                    except Exception as e:
                        st.error(f"Error during authentication: {str(e)}")
        except Exception as e:
            st.error(f"Error initializing Reddit client: {str(e)}")

        st.markdown(
            """
        **Note:** If automatic authentication fails, try:
        1. Ensure your Reddit app is configured correctly as a "web app"
        2. Verify the redirect URI in your Reddit app is exactly: `http://localhost:8080`
        3. Use the manual authentication method, which will provide instructions in the terminal
        """
        )

        # Save the settings
        settings["reddit_client_id"] = reddit_client_id
        if reddit_client_secret:
            settings["reddit_client_secret"] = reddit_client_secret
        else:
            # Keep the original client secret
            settings["reddit_client_secret"] = original_sensitive_settings[
                "reddit_client_secret"
            ]
        settings["reddit_user_agent"] = reddit_user_agent

    with openai_tab:
        st.subheader("OpenAI API Configuration")
        st.info(
            "Configure the OpenAI API for generating responses to negative comments."
        )

        # Check if a valid API key is set
        has_valid_key = (
            settings["openai_api_key"]
            and settings["openai_api_key"] != "your-api-key-here"
        )

        # Show current status of API key
        if has_valid_key:
            st.success("✅ OpenAI API key is configured")
        else:
            st.warning("⚠️ OpenAI API key is not set or contains a placeholder")

        # Help text for API key
        api_key_help = "Get your API key at https://platform.openai.com/api-keys"
        if has_valid_key:
            api_key_help = (
                "API key is already set. Enter a new one only if you want to change it."
            )

        # API key field with better placeholder
        api_key_placeholder = (
            "Leave empty to keep existing key"
            if has_valid_key
            else "No API key set - enter a key"
        )

        api_key = st.text_input(
            "API Key",
            value="",  # Don't show actual key, even masked
            type="password",
            placeholder=api_key_placeholder,
            help=api_key_help,
        )

        # Add test button for API key
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("Test API Key"):
                key_to_test = api_key if api_key else settings["openai_api_key"]
                if not key_to_test:
                    st.error("No API key to test")
                else:
                    with st.spinner("Testing OpenAI API connection..."):
                        success, message = test_openai_api_key(key_to_test)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)

        with col2:
            model = st.selectbox(
                "Model",
                options=["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
                index=(
                    0
                    if settings["openai_model"] == "gpt-4o"
                    else 1 if settings["openai_model"] == "gpt-4-turbo" else 2
                ),
                help="Select the OpenAI model to use for generating responses",
            )

        # Update settings - only update API key if a new one is provided
        if api_key:
            settings["openai_api_key"] = api_key
        else:
            # Keep the original API key
            settings["openai_api_key"] = original_sensitive_settings["openai_api_key"]
        settings["openai_model"] = model

    with general_tab:
        st.subheader("General Settings")

        check_interval = st.number_input(
            "Check Interval (seconds)",
            min_value=30,
            max_value=3600,
            value=int(settings["check_interval"]),
            help="How often to check for new comments (in seconds). Default is 300 seconds (5 minutes).",
        )

        # Update settings
        settings["check_interval"] = str(int(check_interval))

    # Save button
    if st.button("Save Settings"):
        if save_settings(settings):
            st.success(
                "Settings saved successfully! Changes will take effect on the next monitoring session."
            )
        else:
            st.error("Failed to save settings. Please check the logs for details.")


def check_and_restore_monitoring(db: CommentDatabase):
    """Check if monitoring was active before and restore it."""
    monitor_state = load_monitor_state()

    if not monitor_state or not monitor_state.get("active", False):
        return

    # Restore monitoring state
    key_term = monitor_state.get("key_term", "")
    email = monitor_state.get("email", "")
    subreddits = monitor_state.get("subreddits", [])
    start_time = monitor_state.get("start_time")

    if key_term and email and subreddits:
        logger.info(
            f"Restoring monitoring for key term '{key_term}' in subreddits: {', '.join(subreddits)}"
        )

        # Update session state safely
        safe_update_session_state(
            {
                "key_term": key_term,
                "monitor_email": email,
                "monitored_subreddits": subreddits,
                "monitoring_start_time": start_time,
                "monitoring_active": True,
            }
        )

        # Start monitoring
        start_monitoring(key_term, email, subreddits, db)


def display_logs():
    """Display application logs in the GUI."""
    # Create a container for the logs
    log_container = st.container()

    with log_container:
        # Add a clear button and log count in the same row
        col1, col2 = st.columns([5, 1])

        # Get logs first to show the count
        logs = gui_log_handler.get_logs()

        with col1:
            if logs:
                st.markdown(f"Showing {len(logs)} most recent log entries")
            else:
                st.markdown("No logs available")

        with col2:
            if st.button("Clear Logs"):
                gui_log_handler.clear()
                st.rerun()

        # Display logs with styling based on log level
        if not logs:
            st.info("No activity logs to display. Start monitoring to generate logs.")
        else:
            # Create a styled area for logs with custom CSS
            log_area = st.container(border=True)

            with log_area:
                for log in logs:
                    # Format based on log level
                    if "ERROR" in log["level"] or "CRITICAL" in log["level"]:
                        st.markdown(
                            f"❌ `{log['time']}` **{log['level']}**: {log['message']}"
                        )
                    elif "WARNING" in log["level"]:
                        st.markdown(
                            f"⚠️ `{log['time']}` **{log['level']}**: {log['message']}"
                        )
                    else:
                        st.markdown(
                            f"ℹ️ `{log['time']}` **{log['level']}**: {log['message']}"
                        )

                    # Add a separator between log entries for better readability
                    st.markdown("---")


def main():
    """Main function for the Streamlit app."""
    global stop_monitoring

    st.set_page_config(
        page_title="Reddit Sentiment Monitor",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize all critical session state variables
    if "monitoring_active" not in st.session_state:
        st.session_state.monitoring_active = False
    if "monitoring_start_time" not in st.session_state:
        st.session_state.monitoring_start_time = None
    if "last_refresh_time" not in st.session_state:
        st.session_state.last_refresh_time = datetime.now()
    if "last_monitoring_duration" not in st.session_state:
        st.session_state.last_monitoring_duration = None
    if "stop_monitoring_flag" not in st.session_state:
        st.session_state.stop_monitoring_flag = False
    else:
        # Sync the global variable with session state
        stop_monitoring = st.session_state.stop_monitoring_flag

    # Handle any inconsistent states
    # If stopping is in progress but monitoring is inactive, clear the stopping flag
    if st.session_state.get("stopping_in_progress", False):
        if not st.session_state.get("monitoring_active", False):
            logger.info(
                "Clearing stopping_in_progress flag at startup - monitoring already inactive"
            )
            st.session_state.stopping_in_progress = False
        else:
            logger.info("Continuing stop process from previous session")
            # Will be handled in display_monitoring_status

    # Remove any old stop_requested flags
    if "stop_requested" in st.session_state:
        del st.session_state.stop_requested

    # Initialize database
    db = CommentDatabase()

    # Check if monitoring was active before refresh and restore it
    check_and_restore_monitoring(db)

    # Title and description
    st.title("Reddit Sentiment Monitor")
    st.markdown(
        "Monitor Reddit for comments about specific key terms and get email alerts for negative sentiment."
    )

    # Create tabs for main content
    monitor_tab, settings_tab = st.tabs(["Monitor", "Settings"])

    with monitor_tab:
        # Add section headers for better organization
        st.header("Monitoring Status")

        # Display monitoring status at the top of the page
        display_monitoring_status()

        # Create tabs for comments and logs
        comment_tab, log_tab = st.tabs(["Detected Comments", "Activity Logs"])

        with comment_tab:
            # Display detected comments
            st.subheader("Comments")

            # Create tabs for different comment views
            tab1, tab2, tab3 = st.tabs(
                ["All Comments", "Negative Comments", "Pending Responses"]
            )

            # Add refresh button at the top
            col1, col2 = st.columns([5, 1])
            with col2:
                if st.button("🔄 Refresh Comments"):
                    st.rerun()

            with tab1:
                comments = db.get_all_comments()
                if not comments:
                    st.info(
                        "No comments detected yet. Start monitoring to detect new comments."
                    )
                else:
                    display_comments(comments, db=db)

            with tab2:
                negative_comments = db.get_comments_by_sentiment("negative")
                if not negative_comments:
                    st.info("No negative comments detected yet.")
                else:
                    display_comments(negative_comments, db=db)

            with tab3:
                # Track loading state for pending comments tab
                with st.spinner("Loading pending comments..."):
                    pending_comments = db.get_comments_by_status("pending_approval")

                # Check if any responses are being posted
                any_posting_in_progress = False
                if "posting_in_progress" in st.session_state:
                    any_posting_in_progress = any(
                        st.session_state.posting_in_progress.values()
                    )

                # Show loading indicator if any responses are being posted
                if any_posting_in_progress:
                    st.info(
                        "⏳ Posting one or more responses... Please wait for the process to complete."
                    )

                if not pending_comments:
                    st.info("No comments awaiting response.")
                else:
                    # Display pending comments
                    display_comments(pending_comments, show_response=True, db=db)

        with log_tab:
            # Display logs
            display_logs()

    # Sidebar for configuration - preserve the existing code
    with st.sidebar:
        st.header("Configuration")

        # Check if monitoring is active
        monitoring_active = st.session_state.get("monitoring_active", False)

        # Key term input
        key_term = st.text_input(
            "Key Term to Monitor",
            placeholder="e.g., 'Company Name'",
            disabled=monitoring_active,
            value=(
                "" if not monitoring_active else st.session_state.get("key_term", "")
            ),
        )

        # Email input
        email = st.text_input(
            "Email Address for Alerts",
            placeholder="your.email@example.com",
            disabled=monitoring_active,
            value=(
                ""
                if not monitoring_active
                else st.session_state.get("monitor_email", "")
            ),
        )

        # Subreddit selection
        st.subheader("Subreddits to Monitor")
        selected_subreddits = []

        # Default subreddits with checkboxes
        for subreddit in DEFAULT_SUBREDDITS:
            if st.checkbox(
                subreddit,
                value=True,
                disabled=monitoring_active,
                key=f"subreddit_{subreddit}",
            ):
                selected_subreddits.append(subreddit)

        # Custom subreddit input
        custom_subreddit = st.text_input(
            "Add Custom Subreddit", disabled=monitoring_active
        )

        # Only show Add Subreddit button if monitoring is not active
        if custom_subreddit and not monitoring_active:
            if st.button("Add Subreddit"):
                if custom_subreddit not in selected_subreddits:
                    selected_subreddits.append(custom_subreddit)
                    st.success(f"Added {custom_subreddit}")

        # If monitoring is active, use the stored subreddits
        if monitoring_active and "monitored_subreddits" in st.session_state:
            selected_subreddits = st.session_state.monitored_subreddits

            # Display the current monitoring configuration in a formatted box
            st.markdown("---")
            st.markdown("### 🔴 Active Configuration")
            active_config = st.container(border=True)
            with active_config:
                st.markdown(f"**Key Term:** {st.session_state.get('key_term', 'N/A')}")
                st.markdown(
                    f"**Email:** {st.session_state.get('monitor_email', 'N/A')}"
                )
                st.markdown(
                    f"**Subreddits:** {', '.join(st.session_state.get('monitored_subreddits', ['N/A']))}"
                )

                # Get the check interval from session state if available, otherwise from environment
                if "check_interval" in st.session_state:
                    check_interval = st.session_state.check_interval
                else:
                    try:
                        check_interval = int(os.getenv("CHECK_INTERVAL", "300"))
                    except ValueError:
                        check_interval = 300
                st.markdown(f"**Check Interval:** {check_interval} seconds")

                # Show running time
                if "monitoring_start_time" in st.session_state:
                    duration = datetime.now() - st.session_state.monitoring_start_time
                    duration_text = format_duration(duration)
                    st.markdown(f"**Running Time:** {duration_text}")
            st.markdown("---")

        # Start/Stop monitoring buttons with conditional display
        if not monitoring_active:
            # Show start button only if monitoring is not active
            start_button = st.button(
                "▶️ Start Monitoring",
                key="start_monitoring",
                type="primary",
                use_container_width=True,
            )

            if start_button:
                # Check if settings are configured
                settings = load_settings()
                missing_settings = []

                if (
                    not settings["smtp_server"]
                    or not settings["smtp_port"]
                    or not settings["sender_email"]
                    or not settings["sender_email_password"]
                ):
                    missing_settings.append("Email settings")

                if (
                    not settings["reddit_client_id"]
                    or not settings["reddit_client_secret"]
                    or not settings["reddit_user_agent"]
                ):
                    missing_settings.append("Reddit API settings")

                # Check if Reddit authentication is required for posting
                reddit_client = RedditClient()
                if not reddit_client.is_authenticated:
                    st.warning(
                        "⚠️ Reddit account is not authenticated. You will not be able to post responses to comments. "
                        "Go to Settings > Reddit API to authenticate your account."
                    )

                if not settings["openai_api_key"]:
                    missing_settings.append("OpenAI API settings")

                if missing_settings:
                    st.error(
                        f"Please configure the following settings first: {', '.join(missing_settings)}"
                    )
                elif not key_term:
                    st.error("Please enter a key term to monitor")
                elif not email:
                    st.error("Please enter an email address for alerts")
                elif not validate_email(email):
                    st.error("Please enter a valid email address")
                elif not selected_subreddits:
                    st.error("Please select at least one subreddit to monitor")
                else:
                    logger.info(f"Starting monitoring for key term: {key_term}")
                    # Force UI to immediate acknowledge starting
                    with st.spinner("Starting monitoring..."):
                        started = start_monitoring(
                            key_term, email, selected_subreddits, db
                        )
                        if started:
                            # No need for rerun, as start_monitoring function already does this
                            pass
                        else:
                            st.error("Failed to start monitoring. Please check logs.")
        else:
            # Show informative message that monitoring is active
            st.warning("🔴 **MONITORING IS ACTIVE**")
            st.info(
                "Use the **STOP MONITORING** button in the main panel to stop the monitoring process."
            )

    with settings_tab:
        settings_ui()


def display_comments(
    comments: List[Dict], db: CommentDatabase = None, show_response: bool = False
):
    """Display comments in the UI."""
    if not comments:
        st.info("No comments found")
        return

    # Initialize posting state in session state if not exists
    if "posting_in_progress" not in st.session_state:
        st.session_state.posting_in_progress = {}

    # Initialize comment success state if not exists
    if "posting_success" not in st.session_state:
        st.session_state.posting_success = {}

    # Initialize comment error state if not exists
    if "posting_error" not in st.session_state:
        st.session_state.posting_error = {}

    for comment in comments:
        comment_id = comment["id"]
        with st.expander(f"{comment['subreddit']} - {comment['created_utc']}"):
            st.markdown(f"**Comment:** {comment['body']}")
            st.markdown(f"**Author:** {comment['author']}")
            st.markdown(f"**Sentiment:** {comment['sentiment']}")
            st.markdown(f"**Confidence:** {comment['confidence']:.2f}")

            # Fix permalink - make sure it has the Reddit domain prefix
            permalink = comment["permalink"]
            if permalink and not permalink.startswith("http"):
                # Add Reddit domain if it's a relative URL
                permalink = f"https://www.reddit.com{permalink}"

            st.markdown(f"**URL:** [Link to comment]({permalink})")

            if show_response and "ai_response" in comment:
                st.markdown("---")
                st.markdown("**Proposed Response:**")
                response_text = st.text_area(
                    "Response",
                    comment["ai_response"],
                    height=100,
                    key=f"response_{comment_id}",
                )

                # Check if this comment is currently being processed
                if st.session_state.posting_in_progress.get(comment_id, False):
                    st.info("⏳ Posting response... Please wait")

                    # Check if we need to continue the posting process
                    if "reddit_client" not in st.session_state:
                        st.session_state.reddit_client = RedditClient()

                    reddit_client = st.session_state.reddit_client

                    try:
                        # If we need to authenticate, do it now
                        if not reddit_client.is_authenticated:
                            st.warning(
                                "Reddit authentication required. A browser window will open for you to log in to Reddit."
                            )
                            st.info(
                                "Please authorize the application in your browser, then return here."
                            )

                            # Try to authenticate
                            auth_success = reddit_client.authenticate()

                            if not auth_success:
                                st.error(
                                    "Reddit authentication failed. Please try again."
                                )
                                logger.error(
                                    "Reddit authentication failed during comment posting"
                                )
                                st.session_state.posting_in_progress[comment_id] = False
                                st.session_state.posting_error[comment_id] = (
                                    "Authentication failed. Please try again."
                                )
                                st.rerun()
                                continue
                            else:
                                st.success("Authentication successful!")
                                # Give the user time to see the success message
                                time.sleep(1)
                                st.rerun()
                                continue

                        # Check if we can post after authentication
                        if not reddit_client.can_post:
                            error_msg = "Reddit client is authenticated but doesn't have posting permissions. Please ensure you've granted the appropriate permissions during authentication."
                            st.error(error_msg)
                            logger.error(
                                "Cannot post response: Reddit client doesn't have posting permissions"
                            )
                            st.session_state.posting_in_progress[comment_id] = False
                            st.session_state.posting_error[comment_id] = error_msg
                            st.rerun()
                            continue

                        # If we're authenticated and can post, post the response
                        logger.info(
                            f"Attempting to reply to comment with ID: {comment['comment_id']} as user {reddit_client.username}"
                        )

                        # Post the response to Reddit
                        result = reddit_client.reply_to_comment(
                            comment_id=comment["comment_id"],
                            text=response_text,
                        )

                        if result:
                            # Update comment status using approval handler to properly update workflow
                            temp_monitor = RedditMonitor("", "", db=db)
                            temp_monitor.handle_response_approval(comment_id, True)
                            logger.info(
                                f"Successfully posted response to comment {comment_id}"
                            )

                            # Mark as success and stop posting
                            st.session_state.posting_success[comment_id] = True
                            st.session_state.posting_in_progress[comment_id] = False
                            if comment_id in st.session_state.posting_error:
                                del st.session_state.posting_error[comment_id]
                            st.rerun()
                        else:
                            error_msg = "Failed to post response to Reddit. This may be due to rate limits, deleted comment, or insufficient karma."
                            logger.error(
                                f"Failed to post response to comment {comment_id}"
                            )
                            st.session_state.posting_in_progress[comment_id] = False
                            st.session_state.posting_error[comment_id] = error_msg
                            st.rerun()

                    except Exception as e:
                        error_msg = f"Error posting response: {str(e)}"
                        logger.error(error_msg)
                        logger.error(
                            f"Error posting response to comment {comment_id}: {str(e)}"
                        )
                        # Log more details about the error
                        import traceback

                        logger.error(f"Traceback: {traceback.format_exc()}")
                        st.session_state.posting_in_progress[comment_id] = False
                        st.session_state.posting_error[comment_id] = error_msg
                        st.rerun()

                # Display success message if posting was successful
                elif st.session_state.posting_success.get(comment_id, False):
                    st.success("✅ Response successfully posted to Reddit!")

                    # Add a button to hide the success message
                    if st.button("Dismiss", key=f"dismiss_{comment_id}"):
                        st.session_state.posting_success[comment_id] = False
                        st.rerun()

                # Display error message if posting failed
                elif comment_id in st.session_state.posting_error:
                    st.error(f"❌ {st.session_state.posting_error[comment_id]}")

                    # Add a button to try again
                    if st.button("Try Again", key=f"retry_{comment_id}"):
                        del st.session_state.posting_error[comment_id]
                        st.rerun()

                # Allow manual approval from UI if not in progress or already successful
                elif not st.session_state.posting_success.get(comment_id, False):
                    if st.button(
                        "Approve & Post Response", key=f"approve_{comment_id}"
                    ):
                        if db is not None:
                            # Mark as in progress
                            st.session_state.posting_in_progress[comment_id] = True
                            # Initialize Reddit client in session state to persist it
                            st.session_state.reddit_client = RedditClient()

                            # Use the RedditMonitor handle_response_approval to properly handle the workflow
                            try:
                                # Create temporary monitor just for handling the approval
                                temp_monitor = RedditMonitor("", "", db=db)
                                temp_monitor.handle_response_approval(comment_id, True)
                                logger.info(
                                    f"Updated workflow state for comment {comment_id}"
                                )
                            except Exception as e:
                                logger.error(f"Error updating workflow state: {str(e)}")

                            # Rerun to start the posting process
                            st.rerun()
                        else:
                            st.error(
                                "Database connection not available. Cannot update comment status."
                            )


def stop_monitoring_process():
    """Stop monitoring with a single action, no second click needed."""
    global stop_monitoring, monitor_thread, current_monitoring_id, monitoring_threads

    # Phase 1: Initiate stopping (sets flags and shows stopping banner)
    # Phase 2: Complete stopping (clears flags and updates UI)

    # Set global stop flag first for threads to detect
    stop_monitoring = True

    # Set the stop flag in session state so it persists across reruns
    st.session_state.stop_monitoring_flag = True

    # Mark monitoring as inactive immediately
    st.session_state.monitoring_active = False

    # Calculate monitoring duration for display
    if "monitoring_start_time" in st.session_state:
        duration = datetime.now() - st.session_state.monitoring_start_time
        st.session_state.last_monitoring_duration = duration

    # Terminate all monitoring threads
    if monitoring_threads:
        logger.info(f"Stopping {len(monitoring_threads)} monitoring threads")
        for session_id, thread_info in list(monitoring_threads.items()):
            thread = thread_info.get("thread")
            if thread and thread.is_alive():
                try:
                    logger.info(f"Joining thread {session_id} with a 5-second timeout")
                    thread.join(timeout=5)
                    if thread.is_alive():
                        logger.warning(
                            f"Thread {session_id} did not terminate within the timeout"
                        )
                    else:
                        logger.info(f"Thread {session_id} terminated successfully")
                except Exception as e:
                    logger.error(f"Error joining thread {session_id}: {str(e)}")

    # Clear all monitoring data
    monitoring_threads.clear()
    current_monitoring_id = None
    monitor_thread = None

    # Save inactive state to file
    save_monitor_state(active=False)

    # Log completion
    logger.info("Monitoring stopped successfully")

    # Force UI refresh to immediately show stopped state
    try:
        st.rerun()
    except:
        pass


def run_gui():
    """Run the Streamlit GUI."""
    import os
    import sys

    import streamlit.web.cli as stcli

    # Get the path to this file
    file_path = os.path.abspath(__file__)

    # Use sys.argv to pass the file path to streamlit run
    sys.argv = ["streamlit", "run", file_path, "--", "--server.headless", "true"]

    # Run the streamlit app
    sys.exit(stcli.main())


def test_openai_api_key(api_key):
    """Test if the OpenAI API key is valid by making a simple API call."""
    if not api_key:
        return False, "No API key provided"

    try:
        client = OpenAI(api_key=api_key)
        # Make a simple test request
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=5,
        )
        if response and hasattr(response, "choices") and len(response.choices) > 0:
            return True, "API key is valid"
        return False, "Invalid response from OpenAI API"
    except Exception as e:
        return False, f"Error testing API key: {str(e)}"


if __name__ == "__main__":
    main()
