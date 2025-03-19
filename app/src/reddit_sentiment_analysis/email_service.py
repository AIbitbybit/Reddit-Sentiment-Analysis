"""
Email service for sending alerts about negative comments.
Alerts direct users to the GUI for response review and approval.
"""

import logging
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Optional

from dotenv import find_dotenv, load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email alerts about negative comments."""

    def __init__(self):
        """Initialize the email service."""
        # Reload environment variables to ensure we have the latest
        env_path = find_dotenv()
        if env_path:
            load_dotenv(dotenv_path=env_path, override=True)
            logger.info(f"Email service reloaded environment from {env_path}")

            # Check directly if password is in the .env file
            try:
                with open(env_path, "r") as f:
                    env_content = f.read()
                if "SENDER_EMAIL_PASSWORD=" in env_content:
                    lines = env_content.splitlines()
                    for line in lines:
                        if line.startswith("SENDER_EMAIL_PASSWORD="):
                            value = line.split("=", 1)[1].strip() if "=" in line else ""
                            if value:
                                logger.info(
                                    f"Found email password in .env file (length: {len(value)})"
                                )
                                if value == "your_password_here":
                                    logger.warning(
                                        "Email password is set to placeholder 'your_password_here'"
                                    )
                            else:
                                logger.warning("Email password is empty in .env file")
                else:
                    logger.warning("SENDER_EMAIL_PASSWORD not found in .env file")
            except Exception as e:
                logger.warning(f"Error checking .env file directly: {e}")

        # Email configuration
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.sender_password = os.getenv("SENDER_EMAIL_PASSWORD")

        # Log more details about what we loaded
        logger.info(f"SMTP_SERVER: {self.smtp_server}")
        logger.info(f"SMTP_PORT: {self.smtp_port}")
        logger.info(f"SENDER_EMAIL: {self.sender_email}")
        if self.sender_password:
            logger.info(
                f"SENDER_EMAIL_PASSWORD: [set with length {len(self.sender_password)}]"
            )
        else:
            logger.warning("SENDER_EMAIL_PASSWORD is not set")

        # Check for placeholder or default passwords
        placeholders = [
            "your_password_here",
            "your_password",
            "password",
            "yourpassword",
        ]
        if self.sender_password and self.sender_password.lower() in placeholders:
            logger.warning(
                f"Detected placeholder password: {self.sender_password}. Email notifications may not work."
            )

        # Determine if we should use SSL based on port number
        self.use_ssl = self.smtp_port == 465

        # Log configuration
        logger.info(
            f"Email service initialized with server: {self.smtp_server}:{self.smtp_port}"
        )
        logger.info(f"Using {'SSL' if self.use_ssl else 'STARTTLS'} connection")
        logger.info(f"Sender email: {self.sender_email}")

        # Validation
        if not self.sender_email or not self.sender_password:
            logger.warning(
                "Email credentials not found in environment variables. "
                "Email notifications will not work."
            )
        # Additional warning if password looks like a placeholder
        elif self.sender_password and any(
            placeholder in self.sender_password.lower() for placeholder in placeholders
        ):
            logger.warning(
                "Email password appears to be a placeholder. "
                "Please update with a real password for email alerts to work."
            )

    def _create_ssl_context(self):
        """Create an SSL context for email connections."""
        context = ssl.create_default_context()

        # For testing purposes, we can set verify_mode to CERT_NONE
        # WARNING: This should NOT be used in production as it makes the connection insecure
        # Only use this for testing with self-signed certificates
        if os.getenv("EMAIL_SKIP_VERIFY", "false").lower() == "true":
            logger.warning(
                "SSL certificate verification disabled for testing. NOT SECURE FOR PRODUCTION!"
            )
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        else:
            # For production, we attempt to use the system's certificate bundle
            # Look for certifi as an alternative
            try:
                import certifi

                context.load_verify_locations(cafile=certifi.where())
                logger.info(f"Using certifi certificate bundle from: {certifi.where()}")
            except ImportError:
                logger.warning(
                    "certifi package not installed, using system certificates"
                )
                # On some systems, we might need to manually specify the certificate bundle
                # Try common locations
                cert_paths = [
                    "/etc/ssl/certs/ca-certificates.crt",  # Debian/Ubuntu/Gentoo
                    "/etc/pki/tls/certs/ca-bundle.crt",  # Fedora/RHEL
                    "/etc/ssl/ca-bundle.pem",  # OpenSUSE
                    "/etc/pki/tls/cacert.pem",  # OpenELEC
                    "/etc/ssl/cert.pem",  # macOS, FreeBSD
                ]

                for cert_path in cert_paths:
                    if os.path.exists(cert_path):
                        try:
                            context.load_verify_locations(cafile=cert_path)
                            logger.info(
                                f"Using system certificate bundle from: {cert_path}"
                            )
                            break
                        except Exception as e:
                            logger.warning(
                                f"Failed to load certificates from {cert_path}: {e}"
                            )

        return context

    async def send_alert(
        self,
        recipient: str,
        comment_data: Dict,
        sentiment_result: Dict,
        suggested_response: str,
    ) -> bool:
        """
        Send an email alert for a negative comment with AI-generated response.
        The email will direct the user to the GUI for response review and approval.

        Args:
            recipient: Email address to send the alert to
            comment_data: Dictionary containing comment data
            sentiment_result: Dictionary containing sentiment analysis results
            suggested_response: AI-generated response to the comment

        Returns:
            True if email was sent successfully, False otherwise
        """
        # Check for placeholder or empty credentials
        placeholders = [
            "your_password_here",
            "your_password",
            "password",
            "yourpassword",
        ]

        if not self.sender_email:
            logger.error("Sender email not configured. Cannot send alert.")
            return False

        if not self.sender_password:
            logger.error("Email password not configured. Cannot send alert.")
            return False

        if any(
            placeholder.lower() in self.sender_password.lower()
            for placeholder in placeholders
        ):
            logger.error(
                f"Email password appears to be a placeholder: '{self.sender_password}'. Please update it in Settings."
            )
            return False

        try:
            logger.info(
                f"Preparing email alert for negative comment from u/{comment_data['author']}"
            )

            # Create message
            msg = MIMEMultipart()
            msg["Subject"] = f"Negative Comment Alert: {comment_data['subreddit']}"
            msg["From"] = self.sender_email
            msg["To"] = recipient

            # Create email body
            app_url = os.getenv("APP_URL", "http://localhost:8501")
            body = f"""
            <html>
            <body>
                <h2>Negative Comment Detected</h2>
                <p><strong>Subreddit:</strong> {comment_data['subreddit']}</p>
                <p><strong>Author:</strong> {comment_data['author']}</p>
                <p><strong>Comment:</strong> {comment_data['body']}</p>
                <p><strong>Sentiment:</strong> {sentiment_result['sentiment']}</p>
                <p><strong>Confidence:</strong> {sentiment_result['confidence']:.2f}</p>
                
                <p><strong>URL:</strong> <a href="{
                    'https://www.reddit.com' + comment_data['permalink'] if comment_data['permalink'] and not comment_data['permalink'].startswith('http') 
                    else comment_data['permalink']
                }">Link to comment</a></p>
                
                <h3>Proposed AI Response:</h3>
                <div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px;">
                    <p>{suggested_response}</p>
                </div>
                
                <div style="margin-top: 20px; padding: 15px; background-color: #e8f4f8; border-radius: 8px; border-left: 4px solid #2196F3;">
                    <h3 style="margin-top: 0; color: #2196F3;">Review and Approve:</h3>
                    <p>To review and approve this response, please visit the application:</p>
                    <p><a href="{app_url}" style="display: inline-block; background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold;">Open Reddit Sentiment Analysis</a></p>
                    <p>Navigate to the <strong>Pending Responses</strong> tab to manage this and other responses.</p>
                </div>
            </body>
            </html>
            """

            # Attach HTML content
            msg.attach(MIMEText(body, "html"))

            # Send email
            logger.info(
                f"Connecting to SMTP server {self.smtp_server}:{self.smtp_port}"
            )

            # Create SSL context
            context = self._create_ssl_context()

            # Connect using the appropriate method (SSL or STARTTLS)
            if self.use_ssl:
                with smtplib.SMTP_SSL(
                    self.smtp_server, self.smtp_port, context=context
                ) as server:
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls(context=context)
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(msg)

            logger.info(
                f"Successfully sent alert email to {recipient} for comment from u/{comment_data['author']} in r/{comment_data['subreddit']}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")
            return False
