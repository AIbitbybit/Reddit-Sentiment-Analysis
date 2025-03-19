"""
Configuration settings for the Reddit Sentiment Analysis application.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Reddit API Configuration
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv(
    "REDDIT_USER_AGENT", "python:reddit-sentiment-analysis:v0.1.0 (by /u/your_username)"
)
REDDIT_REDIRECT_URI = os.getenv("REDDIT_REDIRECT_URI", "http://localhost:8080")

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
OPENAI_TIMEOUT_SECONDS = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))

# Configure retry settings for the OpenAI client
OPENAI_CONFIG = {
    "max_retries": OPENAI_MAX_RETRIES,
    "timeout": OPENAI_TIMEOUT_SECONDS,
}

# Data Collection Settings
DEFAULT_SUBREDDITS = [
    "smallbusiness",
    "Entrepreneur",
    "business",
    "startups",
    "CustomerService",
]
DEFAULT_TIME_FILTER = "week"  # Options: hour, day, week, month, year, all
DEFAULT_POST_LIMIT = 100
DEFAULT_COMMENT_LIMIT = 25  # Reduced from 50 to 25 to avoid Reddit API rate limiting
BUSINESS_KEYWORDS = [
    "business",
    "company",
    "brand",
    "service",
    "product",
    "customer",
    "experience",
    "review",
    "feedback",
    "quality",
    "price",
    "value",
    "support",
    "store",
    "shop",
    "restaurant",
    "app",
    "website",
]

# Sentiment Analysis Settings
SENTIMENT_CATEGORIES = ["positive", "negative", "neutral"]
CONFIDENCE_THRESHOLD = (
    0.7  # Minimum confidence score to accept sentiment classification
)

# Business Aspects for ABSA
BUSINESS_ASPECTS = [
    "product_quality",
    "customer_service",
    "price_value",
    "user_experience",
    "reliability",
    "delivery",
    "website_app",
    "staff",
    "location",
    "policies",
]

# Storage Settings
VECTOR_DB_PATH = Path("data/vector_db")
RESULTS_DB_PATH = Path("data/results")

# Email Notification Settings
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # App-specific password recommended
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT")  # Where to send notifications
EMAIL_SENDER = os.getenv("EMAIL_SENDER")  # From address for notifications

# How often to refresh data in the application
REFRESH_INTERVAL_MINUTES = 60
