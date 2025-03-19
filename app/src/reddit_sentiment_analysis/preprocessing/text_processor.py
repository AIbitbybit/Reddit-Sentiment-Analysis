"""
Text processor for cleaning and preparing text data for sentiment analysis.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TextProcessor:
    """Processor for cleaning and preparing text data."""

    def __init__(self):
        """Initialize the text processor."""
        logger.info("Text processor initialized")

    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text by cleaning and normalizing it.

        Args:
            text: Text to preprocess

        Returns:
            Preprocessed text
        """
        if not text or not isinstance(text, str):
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r"https?://\S+|www\.\S+", " ", text)

        # Remove Reddit-specific formatting
        text = re.sub(r"\[.*?\]\(.*?\)", " ", text)  # Remove Markdown links
        text = re.sub(r"&amp;", "&", text)  # Replace HTML entities
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)

        # Remove special characters and numbers
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\d+", " ", text)

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text

    def preprocess_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess a Reddit post by cleaning its text fields.

        Args:
            post: Reddit post dictionary

        Returns:
            Preprocessed post dictionary
        """
        processed_post = post.copy()

        # Preprocess title and selftext
        processed_post["processed_title"] = self.preprocess_text(post.get("title", ""))
        processed_post["processed_selftext"] = self.preprocess_text(
            post.get("selftext", "")
        )

        # Combine title and selftext for analysis
        processed_post["processed_content"] = (
            processed_post["processed_title"]
            + " "
            + processed_post["processed_selftext"]
        ).strip()

        # Preprocess comments
        if "comments" in post and isinstance(post["comments"], list):
            processed_comments = []
            for comment in post["comments"]:
                processed_comment = comment.copy()
                processed_comment["processed_body"] = self.preprocess_text(
                    comment.get("body", "")
                )
                processed_comments.append(processed_comment)
            processed_post["processed_comments"] = processed_comments

        return processed_post

    def preprocess_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Preprocess a list of Reddit posts.

        Args:
            posts: List of Reddit post dictionaries

        Returns:
            List of preprocessed post dictionaries
        """
        processed_posts = []

        for post in posts:
            processed_post = self.preprocess_post(post)
            processed_posts.append(processed_post)

        logger.info(f"Preprocessed {len(processed_posts)} posts")
        return processed_posts

    def extract_business_aspects(self, text: str) -> List[str]:
        """
        Extract business aspects from text using simple keyword matching.
        This is a basic implementation and could be enhanced with NLP techniques.

        Args:
            text: Text to extract aspects from

        Returns:
            List of business aspects found in the text
        """
        aspects = []

        # Define aspect keywords
        aspect_keywords = {
            "product_quality": [
                "quality",
                "product",
                "durability",
                "reliability",
                "performance",
            ],
            "customer_service": [
                "service",
                "support",
                "staff",
                "representative",
                "agent",
                "customer service",
            ],
            "price_value": [
                "price",
                "cost",
                "value",
                "expensive",
                "cheap",
                "affordable",
                "worth",
            ],
            "user_experience": [
                "experience",
                "user",
                "interface",
                "usability",
                "easy to use",
                "difficult",
            ],
            "reliability": [
                "reliable",
                "consistent",
                "dependable",
                "trust",
                "trustworthy",
            ],
            "delivery": ["delivery", "shipping", "arrive", "package", "shipment"],
            "website_app": [
                "website",
                "app",
                "application",
                "site",
                "online",
                "mobile",
            ],
            "staff": ["employee", "staff", "worker", "manager", "team"],
            "location": ["location", "store", "branch", "office", "place"],
            "policies": [
                "policy",
                "policies",
                "terms",
                "conditions",
                "rules",
                "return",
            ],
        }

        # Check for each aspect
        for aspect, keywords in aspect_keywords.items():
            if any(keyword in text for keyword in keywords):
                aspects.append(aspect)

        return aspects
