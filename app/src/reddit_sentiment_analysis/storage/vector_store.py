"""
Vector store for storing and retrieving analysis results using ChromaDB.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from ..config import VECTOR_DB_PATH

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SentimentVectorStore:
    """Vector store for sentiment analysis results."""

    def __init__(
        self,
        persist_directory: Union[str, Path] = VECTOR_DB_PATH,
        collection_name: str = "reddit_sentiment",
    ):
        """
        Initialize the vector store.

        Args:
            persist_directory: Directory to persist the vector store
            collection_name: Name of the collection
        """
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name

        # Create directory if it doesn't exist
        os.makedirs(self.persist_directory, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False),
        )

        # Use OpenAI embeddings
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.environ.get("OPENAI_API_KEY"),
            model_name="text-embedding-ada-002",
        )

        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name, embedding_function=self.embedding_function
            )
            logger.info(f"Using existing collection: {self.collection_name}")
        except (ValueError, Exception) as e:
            # Handle both ValueError and InvalidCollectionException
            logger.info(
                f"Collection {self.collection_name} does not exist. Creating it now."
            )
            self.collection = self.client.create_collection(
                name=self.collection_name, embedding_function=self.embedding_function
            )
            logger.info(f"Created new collection: {self.collection_name}")

    def add_result(self, result: Dict[str, Any]) -> str:
        """
        Add a sentiment analysis result to the vector store.

        Args:
            result: Sentiment analysis result

        Returns:
            ID of the added document
        """
        # Extract post ID
        post_id = result.get("post_id")
        if not post_id:
            raise ValueError("Result must have a post_id")

        # Create document ID
        doc_id = f"post_{post_id}"

        # Create document text for embedding
        title = result.get("title", "")
        overall_sentiment = result.get("overall_sentiment", "")
        content_sentiment_explanation = result.get("content_sentiment", {}).get(
            "explanation", ""
        )

        # Combine aspect explanations
        aspect_explanations = []
        for aspect_result in result.get("aspect_sentiments", []):
            aspect = aspect_result.get("aspect", "")
            sentiment = aspect_result.get("sentiment", "")
            explanation = aspect_result.get("explanation", "")
            aspect_explanations.append(f"{aspect}: {sentiment} - {explanation}")

        # Create document text
        document_text = f"Title: {title}\nOverall Sentiment: {overall_sentiment}\n"
        document_text += f"Content Sentiment: {content_sentiment_explanation}\n"
        document_text += "Aspect Sentiments:\n" + "\n".join(aspect_explanations)

        # Create metadata
        metadata = {
            "post_id": post_id,
            "subreddit": result.get("subreddit", ""),
            "overall_sentiment": overall_sentiment,
            "overall_confidence": result.get("overall_confidence", 0),
            "has_comments": result.get("has_comments", False),
            "comment_count": result.get("comment_count", 0),
        }

        # Add document to collection
        try:
            self.collection.upsert(
                ids=[doc_id], documents=[document_text], metadatas=[metadata]
            )
            logger.info(f"Added result for post {post_id} to vector store")
            return doc_id
        except Exception as e:
            logger.error(f"Error adding result to vector store: {str(e)}")
            raise

    def add_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """
        Add multiple sentiment analysis results to the vector store.

        Args:
            results: List of sentiment analysis results

        Returns:
            List of document IDs
        """
        doc_ids = []
        for result in results:
            try:
                doc_id = self.add_result(result)
                doc_ids.append(doc_id)
            except Exception as e:
                logger.error(f"Error adding result: {str(e)}")

        return doc_ids

    def search(
        self,
        query: str,
        filter_metadata: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for sentiment analysis results.

        Args:
            query: Search query
            filter_metadata: Metadata filter
            limit: Maximum number of results

        Returns:
            List of matching results
        """
        try:
            results = self.collection.query(
                query_texts=[query], n_results=limit, where=filter_metadata
            )

            # Format results
            formatted_results = []
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                document = results["documents"][0][i]
                distance = (
                    results.get("distances", [[]])[0][i]
                    if "distances" in results
                    else None
                )

                formatted_result = {
                    "id": doc_id,
                    "metadata": metadata,
                    "document": document,
                    "distance": distance,
                }
                formatted_results.append(formatted_result)

            logger.info(f"Found {len(formatted_results)} results for query: {query}")
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching vector store: {str(e)}")
            return []

    def get_by_post_id(self, post_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a sentiment analysis result by post ID.

        Args:
            post_id: Post ID

        Returns:
            Sentiment analysis result or None if not found
        """
        doc_id = f"post_{post_id}"

        try:
            result = self.collection.get(
                ids=[doc_id], include=["metadatas", "documents"]
            )

            if not result["ids"]:
                return None

            return {
                "id": result["ids"][0],
                "metadata": result["metadatas"][0],
                "document": result["documents"][0],
            }
        except Exception as e:
            logger.error(f"Error getting result by post ID: {str(e)}")
            return None

    def filter_by_sentiment(
        self, sentiment: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Filter results by sentiment.

        Args:
            sentiment: Sentiment to filter by (positive, negative, neutral)
            limit: Maximum number of results

        Returns:
            List of matching results
        """
        try:
            results = self.collection.get(
                where={"overall_sentiment": sentiment}, limit=limit
            )

            # Format results
            formatted_results = []
            for i, doc_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i]
                document = results["documents"][i]

                formatted_result = {
                    "id": doc_id,
                    "metadata": metadata,
                    "document": document,
                }
                formatted_results.append(formatted_result)

            logger.info(
                f"Found {len(formatted_results)} results with sentiment: {sentiment}"
            )
            return formatted_results
        except Exception as e:
            logger.error(f"Error filtering by sentiment: {str(e)}")
            return []

    def get_sentiment_distribution(self) -> Dict[str, int]:
        """
        Get the distribution of sentiments.

        Returns:
            Dictionary with sentiment counts
        """
        try:
            # Get all results
            results = self.collection.get()

            # Count sentiments
            sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}

            for metadata in results["metadatas"]:
                sentiment = metadata.get("overall_sentiment")
                if sentiment in sentiment_counts:
                    sentiment_counts[sentiment] += 1

            return sentiment_counts
        except Exception as e:
            logger.error(f"Error getting sentiment distribution: {str(e)}")
            return {"positive": 0, "negative": 0, "neutral": 0}
