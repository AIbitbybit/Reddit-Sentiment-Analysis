"""
Sentiment analyzer using LangChain and OpenAI.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ..config import (
    CONFIDENCE_THRESHOLD,
    OPENAI_API_KEY,
    OPENAI_CONFIG,
    OPENAI_MODEL,
    SENTIMENT_CATEGORIES,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Define output schemas
class SentimentResult(BaseModel):
    """Schema for sentiment analysis result."""

    sentiment: str = Field(
        description="The sentiment of the text (positive, negative, or neutral)"
    )
    confidence: float = Field(description="Confidence score between 0 and 1")
    explanation: str = Field(
        description="Brief explanation of the sentiment classification"
    )


class AspectSentimentResult(BaseModel):
    """Schema for aspect-based sentiment analysis result."""

    aspect: str = Field(description="The business aspect being analyzed")
    sentiment: str = Field(
        description="The sentiment for this aspect (positive, negative, or neutral)"
    )
    confidence: float = Field(description="Confidence score between 0 and 1")
    explanation: str = Field(
        description="Brief explanation of the sentiment classification for this aspect"
    )


class SentimentAnalyzer:
    """Sentiment analyzer using LangChain and OpenAI."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
    ):
        """
        Initialize the sentiment analyzer.

        Args:
            api_key: OpenAI API key
            model_name: OpenAI model name
            temperature: Temperature for the model (0.0 = deterministic)
        """
        self.api_key = api_key or OPENAI_API_KEY
        self.model_name = model_name or OPENAI_MODEL
        self.temperature = temperature

        if not self.api_key:
            logger.warning(
                "OpenAI API key is missing or empty. Sentiment analysis may fail."
            )

        # Initialize LLM with retry and timeout settings
        self.llm = ChatOpenAI(
            api_key=self.api_key,
            model=self.model_name,
            temperature=self.temperature,
            max_retries=OPENAI_CONFIG["max_retries"],
            request_timeout=OPENAI_CONFIG["timeout"],
        )

        # Initialize output parsers
        self.sentiment_parser = JsonOutputParser(pydantic_object=SentimentResult)
        self.aspect_sentiment_parser = JsonOutputParser(
            pydantic_object=AspectSentimentResult
        )

        # Create sentiment analysis prompt
        self.sentiment_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a sentiment analysis expert. Analyze the sentiment of the given text and classify it as positive, negative, or neutral.
            
Provide a confidence score between 0 and 1, where:
- 0.0-0.4: Low confidence
- 0.4-0.7: Medium confidence
- 0.7-1.0: High confidence

Also provide a brief explanation of your classification.

Format your response as a JSON object with the following fields:
- sentiment: The sentiment classification (positive, negative, or neutral)
- confidence: A float between 0 and 1 representing your confidence
- explanation: A brief explanation of your classification""",
                ),
                ("user", "{text}"),
            ]
        )

        # Create aspect-based sentiment analysis prompt
        self.aspect_sentiment_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a business sentiment analysis expert. Analyze the sentiment of the given text specifically for the specified business aspect.
            
Classify the sentiment as positive, negative, or neutral for the given aspect only.

Provide a confidence score between 0 and 1, where:
- 0.0-0.4: Low confidence
- 0.4-0.7: Medium confidence
- 0.7-1.0: High confidence

Also provide a brief explanation of your classification.

Format your response as a JSON object with the following fields:
- aspect: The business aspect being analyzed (repeat the input aspect)
- sentiment: The sentiment classification for this aspect (positive, negative, or neutral)
- confidence: A float between 0 and 1 representing your confidence
- explanation: A brief explanation of your classification""",
                ),
                ("user", "Text: {text}\nAspect: {aspect}"),
            ]
        )

        # Create sentiment analysis chain
        self.sentiment_chain = self.sentiment_prompt | self.llm | self.sentiment_parser

        # Create aspect-based sentiment analysis chain
        self.aspect_sentiment_chain = (
            self.aspect_sentiment_prompt | self.llm | self.aspect_sentiment_parser
        )

        logger.info(f"Sentiment analyzer initialized with model: {self.model_name}")

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze the sentiment of a text.

        Args:
            text: Text to analyze

        Returns:
            Sentiment analysis result
        """
        if not text or not isinstance(text, str) or len(text.strip()) == 0:
            return {
                "sentiment": "neutral",
                "confidence": 0.0,
                "explanation": "Empty or invalid text",
            }

        try:
            result = await self.sentiment_chain.ainvoke({"text": text})
            return result
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {
                "sentiment": "neutral",
                "confidence": 0.0,
                "explanation": f"Error: {str(e)}",
            }

    async def analyze_aspect_sentiment(self, text: str, aspect: str) -> Dict[str, Any]:
        """
        Analyze the sentiment of a text for a specific business aspect.

        Args:
            text: Text to analyze
            aspect: Business aspect to analyze

        Returns:
            Aspect-based sentiment analysis result
        """
        if not text or not isinstance(text, str) or len(text.strip()) == 0:
            return {
                "aspect": aspect,
                "sentiment": "neutral",
                "confidence": 0.0,
                "explanation": "Empty or invalid text",
            }

        try:
            result = await self.aspect_sentiment_chain.ainvoke(
                {"text": text, "aspect": aspect}
            )
            return result
        except Exception as e:
            logger.error(f"Error analyzing aspect sentiment: {str(e)}")
            return {
                "aspect": aspect,
                "sentiment": "neutral",
                "confidence": 0.0,
                "explanation": f"Error: {str(e)}",
            }

    async def analyze_post(
        self, post: Dict[str, Any], analyze_comments: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze the sentiment of a Reddit post.

        Args:
            post: Reddit post dictionary (preprocessed)
            analyze_comments: Whether to analyze comments

        Returns:
            Post with sentiment analysis results
        """
        analyzed_post = post.copy()

        # Analyze post content
        content_text = post.get("processed_content", "")
        if content_text:
            content_sentiment = await self.analyze_sentiment(content_text)
            analyzed_post["content_sentiment"] = content_sentiment

        # Extract and analyze business aspects
        from ..preprocessing.text_processor import TextProcessor

        text_processor = TextProcessor()
        aspects = text_processor.extract_business_aspects(content_text)

        if aspects:
            aspect_sentiments = []
            for aspect in aspects:
                aspect_sentiment = await self.analyze_aspect_sentiment(
                    content_text, aspect
                )
                aspect_sentiments.append(aspect_sentiment)
            analyzed_post["aspect_sentiments"] = aspect_sentiments

        # Analyze comments
        if (
            analyze_comments
            and "processed_comments" in post
            and isinstance(post["processed_comments"], list)
        ):
            analyzed_comments = []
            for comment in post["processed_comments"]:
                analyzed_comment = comment.copy()
                comment_text = comment.get("processed_body", "")
                if comment_text:
                    comment_sentiment = await self.analyze_sentiment(comment_text)
                    analyzed_comment["sentiment"] = comment_sentiment

                    # Extract and analyze business aspects in comments
                    comment_aspects = text_processor.extract_business_aspects(
                        comment_text
                    )
                    if comment_aspects:
                        comment_aspect_sentiments = []
                        for aspect in comment_aspects:
                            aspect_sentiment = await self.analyze_aspect_sentiment(
                                comment_text, aspect
                            )
                            comment_aspect_sentiments.append(aspect_sentiment)
                        analyzed_comment["aspect_sentiments"] = (
                            comment_aspect_sentiments
                        )

                analyzed_comments.append(analyzed_comment)
            analyzed_post["analyzed_comments"] = analyzed_comments

        return analyzed_post

    async def analyze_posts(
        self, posts: List[Dict[str, Any]], analyze_comments: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Analyze the sentiment of a list of Reddit posts.

        Args:
            posts: List of Reddit post dictionaries (preprocessed)
            analyze_comments: Whether to analyze comments

        Returns:
            List of posts with sentiment analysis results
        """
        analyzed_posts = []

        for post in posts:
            analyzed_post = await self.analyze_post(
                post, analyze_comments=analyze_comments
            )
            analyzed_posts.append(analyzed_post)

        logger.info(f"Analyzed sentiment for {len(analyzed_posts)} posts")
        return analyzed_posts
