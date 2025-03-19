"""
Response generator for drafting replies to negative comments.
"""

import logging
import os
from typing import Dict, Optional

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generate AI responses to negative comments."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the response generator.

        Args:
            model_name: OpenAI model name to use
        """
        # Get API key and model from environment
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o")

        if not self.api_key:
            logger.warning("OpenAI API key not found in environment variables")

        # Initialize LLM
        self.llm = ChatOpenAI(
            api_key=self.api_key,
            model=self.model_name,
            temperature=0.7,  # Slightly creative responses
        )

        # Create response generation prompt
        self.response_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a professional customer service representative for a company. 
Your task is to draft a thoughtful, empathetic response to a negative comment about your company or product.

Guidelines for your response:
1. Be empathetic and acknowledge the customer's concerns
2. Maintain a professional and respectful tone
3. Offer a solution or next steps when possible
4. Keep the response concise (3-5 sentences)
5. Do not be defensive or argumentative
6. Do not make specific promises you can't keep
7. Be authentic and human-sounding

The comment is from Reddit, so make sure your response is appropriate for that platform.
""",
                ),
                (
                    "user",
                    """Respond to this negative comment:

Subreddit: {subreddit}
Author: {author}
Comment: {comment}

Draft a response that addresses their concerns professionally:""",
                ),
            ]
        )

        logger.info(f"Initialized response generator with model: {self.model_name}")

    async def generate_response(self, comment_data: Dict) -> str:
        """
        Generate a response to a negative comment.

        Args:
            comment_data: Dictionary containing comment data

        Returns:
            Generated response text
        """
        if not self.api_key:
            logger.error("Cannot generate response: OpenAI API key not configured")
            return "I apologize for your negative experience. Our team will review your feedback and get back to you soon."

        try:
            # Extract comment data
            subreddit = comment_data.get("subreddit", "")
            author = comment_data.get("author", "")
            comment_text = comment_data.get("body", "")

            # Generate response
            response = await self.llm.ainvoke(
                self.response_prompt.format(
                    subreddit=subreddit, author=author, comment=comment_text
                )
            )

            response_text = response.content

            logger.info(f"Generated response for comment by {author} in r/{subreddit}")
            return response_text

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I apologize for your negative experience. Our team will review your feedback and get back to you soon."
