"""
Reddit client for fetching posts and comments from Reddit.
"""

import json
import logging
import os
import socket
import time
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import praw
import requests_cache
from prawcore.exceptions import OAuthException, ResponseException
from tqdm import tqdm

from ..config import (
    BUSINESS_KEYWORDS,
    DEFAULT_COMMENT_LIMIT,
    DEFAULT_POST_LIMIT,
    DEFAULT_SUBREDDITS,
    DEFAULT_TIME_FILTER,
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_REDIRECT_URI,
    REDDIT_USER_AGENT,
)
from ..utils.rate_limiting import throttle, with_retry

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define token path
TOKEN_PATH = Path(__file__).parent.parent.parent.parent / "reddit_token.json"

# Set up requests cache to avoid hitting rate limits
requests_cache.install_cache(
    cache_name=str(
        Path(__file__).parent.parent.parent.parent / "data" / "reddit_cache"
    ),
    backend="sqlite",
    expire_after=timedelta(minutes=10),  # Cache responses for 10 minutes
)
logger.info("Installed requests cache for Reddit API")


class RedditClient:
    """Client for interacting with the Reddit API."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        """
        Initialize the Reddit client.

        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: Reddit API user agent
            username: Reddit username (for legacy password auth, not used in OAuth)
            password: Reddit password (for legacy password auth, not used in OAuth)
            redirect_uri: Redirect URI for OAuth flow
        """
        self.client_id = client_id or REDDIT_CLIENT_ID
        self.client_secret = client_secret or REDDIT_CLIENT_SECRET
        self.user_agent = user_agent or REDDIT_USER_AGENT
        self.username = username or os.getenv("REDDIT_USERNAME")
        self.password = password or os.getenv("REDDIT_PASSWORD")
        self.redirect_uri = redirect_uri or REDDIT_REDIRECT_URI
        self.scopes = ["identity", "read", "submit"]
        self.can_post = False
        self.is_authenticated = False

        if not all([self.client_id, self.client_secret, self.user_agent]):
            raise ValueError(
                "Reddit API credentials are missing. Please set them in the .env file."
            )

        # Try to initialize using tokens first
        if self._try_token_auth():
            logger.info("Authenticated using saved token")
            self.can_post = True
            self.is_authenticated = True
        else:
            # Fall back to read-only mode
            logger.warning("Using read-only mode (cannot post)")
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
            )
            self.is_authenticated = False
            self.can_post = False

        logger.info("Reddit client initialized successfully")

    def _try_token_auth(self) -> bool:
        """Try to authenticate using stored refresh token."""
        if not TOKEN_PATH.exists():
            logger.info("No saved tokens found")
            return False

        try:
            with open(TOKEN_PATH, "r") as f:
                token_data = json.load(f)

            refresh_token = token_data.get("refresh_token")
            if not refresh_token:
                logger.warning("Refresh token not found in saved data")
                return False

            logger.info("Found refresh token, attempting to authenticate")
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
                refresh_token=refresh_token,
            )

            # Verify the authentication worked
            username = self.reddit.user.me().name
            logger.info(f"Successfully authenticated as u/{username}")
            self.username = username
            return True

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error reading token file: {str(e)}")
            return False
        except (OAuthException, ResponseException) as e:
            logger.error(f"OAuth error with saved token: {str(e)}")
            # Token might be expired or invalid, delete it
            TOKEN_PATH.unlink(missing_ok=True)
            return False
        except Exception as e:
            logger.error(f"Error authenticating with token: {str(e)}")
            return False

    def authenticate(self) -> bool:
        """
        Authenticate with Reddit using OAuth.

        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        try:
            # Initialize a new Reddit instance for OAuth
            reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                user_agent=self.user_agent,
            )

            # Generate the authorization URL
            state = "sentinel"
            scopes = ["identity", "read", "submit"]
            auth_url = reddit.auth.url(scopes=scopes, state=state)

            logger.info(f"Opening browser for Reddit authentication...")
            logger.info(f"Please authorize the application in your browser")
            logger.info(f"Redirect URI: {self.redirect_uri}")
            logger.info(f"Authorization URL: {auth_url}")

            # Open the URL in the user's browser
            webbrowser.open(auth_url)

            # Parse the port from the redirect URI
            parsed_port = 8080  # Default port
            if self.redirect_uri and ":" in self.redirect_uri.split("/")[-1]:
                try:
                    parsed_port = int(self.redirect_uri.split(":")[-1])
                    logger.info(f"Using port {parsed_port} from redirect URI")
                except (ValueError, IndexError):
                    logger.warning(
                        f"Could not parse port from redirect URI, using default port 8080"
                    )

            # Set up a simple HTTP server to catch the callback
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("localhost", parsed_port))
            server.listen(1)
            server.settimeout(120)  # 2 minute timeout

            logger.info(f"Waiting for callback from Reddit on port {parsed_port}...")

            try:
                # Accept the callback
                client, _ = server.accept()
                data = client.recv(1024).decode("utf-8")
                logger.info("Received callback data")

                # Debug the raw callback data
                logger.info(f"Raw callback data: {data}")

                # Extract the code from the request
                if "code=" not in data:
                    logger.error("No authorization code found in callback data")
                    response = "HTTP/1.1 400 Bad Request\r\n\r\n<html><body><h1>Error</h1><p>No authorization code found.</p></body></html>"
                    client.send(response.encode("utf-8"))
                    client.close()
                    server.close()
                    return False

                # Parse the request line more carefully
                request_line = data.split("\n")[0]
                logger.info(f"Request line: {request_line}")

                # More robust parsing of the authorization code
                code = None
                request_parts = request_line.split(" ")
                if len(request_parts) > 1:
                    path = request_parts[1]
                    if "?" in path:
                        query_string = path.split("?")[1]
                        params = query_string.split("&")
                        for param in params:
                            if param.startswith("code="):
                                code = param.split("=")[1]
                                break

                if not code:
                    logger.error("Failed to extract authorization code from callback")
                    response = "HTTP/1.1 400 Bad Request\r\n\r\n<html><body><h1>Error</h1><p>Failed to extract authorization code.</p></body></html>"
                    client.send(response.encode("utf-8"))
                    client.close()
                    server.close()
                    return False

                logger.info("Authorization code extracted successfully")

                # Send a simple response to the browser
                response = "HTTP/1.1 200 OK\r\n\r\n<html><head><title>Authentication Successful</title></head>"
                response += "<body><h1>Authentication Successful!</h1>"
                response += "<p>You can now close this window and return to the application.</p></body></html>"
                client.send(response.encode("utf-8"))
                client.close()

            except socket.timeout:
                logger.error("Timeout waiting for callback")
                server.close()
                return False
            except Exception as e:
                logger.error(f"Error during callback handling: {str(e)}")
                server.close()
                return False
            finally:
                server.close()

            # Exchange the code for a refresh token
            try:
                logger.info("Exchanging authorization code for refresh token...")
                refresh_token = reddit.auth.authorize(code)
                logger.info(
                    "Successfully exchanged authorization code for refresh token"
                )

                # Save the token for future use
                token_data = {"refresh_token": refresh_token}

                with open(TOKEN_PATH, "w") as f:
                    json.dump(token_data, f)

                logger.info(f"Token saved successfully to {TOKEN_PATH}")

                # Update the instance to use the authenticated client
                self.reddit = reddit
                self.can_post = True
                self.is_authenticated = True
                self.username = self.reddit.user.me().name

                logger.info(f"Successfully authenticated as u/{self.username}")
                return True
            except ResponseException as e:
                logger.error(f"Reddit API error during token exchange: {str(e)}")
                logger.error(f"Status code: {e.response.status_code}")
                logger.error(
                    f"Response body: {e.response.text if hasattr(e.response, 'text') else 'No response text'}"
                )

                # Provide more specific guidance based on error code
                if e.response.status_code == 400:
                    logger.error("A 400 error usually means:")
                    logger.error(
                        "1. The redirect URI in your Reddit app settings doesn't EXACTLY match the one in the code"
                    )
                    logger.error(f"   - Code is using: {self.redirect_uri}")
                    logger.error(
                        "2. Your app might not be set as a 'web app' type on Reddit"
                    )
                    logger.error(
                        "3. Your client ID or client secret might be incorrect"
                    )
                    logger.error(
                        "\nPlease visit https://www.reddit.com/prefs/apps to check your app settings"
                    )
                elif e.response.status_code == 401:
                    logger.error("A 401 error suggests your credentials are incorrect")
                elif e.response.status_code == 403:
                    logger.error(
                        "A 403 error suggests you don't have permission for this action"
                    )

                return False
            except Exception as e:
                logger.error(f"Error during token exchange: {str(e)}")
                import traceback

                logger.error(f"Traceback: {traceback.format_exc()}")
                return False

        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def authenticate_manual(self) -> bool:
        """
        Authenticate with Reddit using a manual OAuth flow.
        This method does not require a callback server and is useful when the automatic flow fails.

        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        try:
            # Initialize a new Reddit instance for OAuth
            reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                user_agent=self.user_agent,
            )

            # Generate the authorization URL
            state = "sentinel"
            scopes = ["identity", "read", "submit"]
            auth_url = reddit.auth.url(scopes=scopes, state=state)

            logger.info(
                f"Please open this URL in your browser to authorize the application:"
            )
            logger.info(f"\n{auth_url}\n")
            logger.info(
                "After authorizing, you will be redirected to your redirect URI."
            )
            logger.info(
                "You'll see an error page because localhost isn't running a server."
            )
            logger.info("That's OK! Look in your browser's address bar for the URL.")
            logger.info(
                "The URL will contain a 'code' parameter after '?code=' and before '&state='"
            )
            logger.info(
                "Example: http://localhost:8080?code=YOUR_CODE_HERE&state=sentinel"
            )

            # Ask user to input the code
            print("\n" + "=" * 80)
            print("COPY THE AUTHORIZATION CODE FROM THE URL IN YOUR BROWSER")
            print(
                "Look for the part after '?code=' and before '&state=' or at the end of the URL"
            )
            print("=" * 80 + "\n")

            code = input("Paste the authorization code here: ").strip()

            if not code:
                logger.error("No authorization code provided")
                return False

            # Clean up the code if user copied more than just the code
            # First remove any hash fragments
            if "#" in code:
                code = code.split("#")[0]
                logger.info("Removed hash fragment from code")

            # Then try to extract the code from various formats
            if "code=" in code:
                # Extract just the code part
                try:
                    # Try to extract from a full URL
                    if "?" in code and "&" in code:
                        params = code.split("?")[1].split("&")
                        for param in params:
                            if param.startswith("code="):
                                code = param.split("=")[1]
                                break
                    # Or just from the code= part
                    elif "code=" in code:
                        code = (
                            code.split("code=")[1].split("&")[0]
                            if "&" in code
                            else code.split("code=")[1]
                        )

                    logger.info(f"Extracted authorization code: {code[:5]}...")
                except Exception as e:
                    logger.warning(f"Could not parse code from input: {str(e)}")
                    logger.warning("Using the raw input as the code")

            logger.info(f"Using code: {code[:5]}... (length: {len(code)})")
            logger.info("Authorization code received, exchanging for refresh token...")

            try:
                # Exchange the code for a refresh token
                refresh_token = reddit.auth.authorize(code)
                logger.info(
                    "Successfully exchanged authorization code for refresh token"
                )

                # Save the token for future use
                token_data = {"refresh_token": refresh_token}

                with open(TOKEN_PATH, "w") as f:
                    json.dump(token_data, f)

                logger.info(f"Token saved successfully to {TOKEN_PATH}")

                # Update the instance to use the authenticated client
                self.reddit = reddit
                self.can_post = True
                self.is_authenticated = True
                self.username = self.reddit.user.me().name

                logger.info(f"Successfully authenticated as u/{self.username}")
                return True

            except ResponseException as e:
                logger.error(f"Reddit API error during token exchange: {str(e)}")
                logger.error(f"Status code: {e.response.status_code}")
                logger.error(
                    f"Response body: {e.response.text if hasattr(e.response, 'text') else 'No response text'}"
                )

                # Provide more specific guidance based on error code
                if e.response.status_code == 400:
                    logger.error("The provided code was invalid or has expired.")
                    logger.error(
                        "Please try again and make sure to copy the entire code correctly."
                    )
                    logger.error(
                        "The code should look something like: 'G7UaQSQX5qMlEIGl0GIzO6fIELU'"
                    )

                    # Suggest updating Reddit app settings
                    logger.error("\nPlease verify your Reddit app settings:")
                    logger.error(f"1. Go to https://www.reddit.com/prefs/apps")
                    logger.error(f"2. Ensure your app is set as a 'web app' type")
                    logger.error(
                        f"3. Ensure the redirect URI is exactly: {self.redirect_uri}"
                    )
                    logger.error(f"4. Double-check your client ID and client secret")

                elif e.response.status_code == 401:
                    logger.error("A 401 error suggests your credentials are incorrect")

                return False

        except Exception as e:
            logger.error(f"Error during manual authentication: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def fetch_posts(
        self,
        subreddits: List[str] = None,
        time_filter: str = DEFAULT_TIME_FILTER,
        limit: int = DEFAULT_POST_LIMIT,
        filter_business: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Fetch posts from specified subreddits.

        Args:
            subreddits: List of subreddit names to fetch posts from
            time_filter: Time filter for posts (hour, day, week, month, year, all)
            limit: Maximum number of posts to fetch per subreddit
            filter_business: Whether to filter posts for business-related content

        Returns:
            List of post dictionaries
        """
        subreddits = subreddits or DEFAULT_SUBREDDITS
        all_posts = []

        for subreddit_name in tqdm(subreddits, desc="Fetching subreddits"):
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                posts = subreddit.top(time_filter=time_filter, limit=limit)

                for post in tqdm(
                    posts, desc=f"Processing posts from r/{subreddit_name}", leave=False
                ):
                    # Skip non-business posts if filtering is enabled
                    if filter_business and not self._is_business_related(
                        post.title + " " + post.selftext
                    ):
                        continue

                    post_data = {
                        "id": post.id,
                        "subreddit": subreddit_name,
                        "title": post.title,
                        "selftext": post.selftext,
                        "score": post.score,
                        "upvote_ratio": post.upvote_ratio,
                        "url": post.url,
                        "created_utc": post.created_utc,
                        "num_comments": post.num_comments,
                        "permalink": post.permalink,
                        "comments": self._fetch_comments(
                            post, limit=DEFAULT_COMMENT_LIMIT
                        ),
                    }
                    all_posts.append(post_data)

            except Exception as e:
                logger.error(f"Error fetching posts from r/{subreddit_name}: {str(e)}")

        logger.info(
            f"Fetched {len(all_posts)} business-related posts from {len(subreddits)} subreddits"
        )
        return all_posts

    def _fetch_comments(
        self, post, limit: int = DEFAULT_COMMENT_LIMIT
    ) -> List[Dict[str, Any]]:
        """
        Fetch comments for a post.

        Args:
            post: PRAW post object
            limit: Maximum number of comments to fetch

        Returns:
            List of comment dictionaries
        """
        comments = []
        post.comments.replace_more(limit=0)  # Remove MoreComments objects

        for comment in post.comments.list()[:limit]:
            try:
                comment_data = {
                    "id": comment.id,
                    "body": comment.body,
                    "score": comment.score,
                    "created_utc": comment.created_utc,
                    "is_submitter": comment.is_submitter,
                    "permalink": comment.permalink,
                }
                comments.append(comment_data)
            except Exception as e:
                logger.error(f"Error processing comment {comment.id}: {str(e)}")

        return comments

    def _is_business_related(self, text: str) -> bool:
        """
        Check if text is related to business based on keywords.

        Args:
            text: Text to check

        Returns:
            True if text contains business-related keywords, False otherwise
        """
        text = text.lower()
        return any(keyword in text for keyword in BUSINESS_KEYWORDS)

    def search_posts(
        self,
        query: str,
        subreddits: List[str] = None,
        time_filter: str = DEFAULT_TIME_FILTER,
        limit: int = DEFAULT_POST_LIMIT,
    ) -> List[Dict[str, Any]]:
        """
        Search for posts matching a query.

        Args:
            query: Search query
            subreddits: List of subreddit names to search in
            time_filter: Time filter for posts
            limit: Maximum number of posts to fetch

        Returns:
            List of post dictionaries
        """
        subreddits = subreddits or DEFAULT_SUBREDDITS
        all_posts = []

        for subreddit_name in tqdm(subreddits, desc="Searching subreddits"):
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                search_results = subreddit.search(
                    query, time_filter=time_filter, limit=limit
                )

                for post in tqdm(
                    search_results,
                    desc=f"Processing search results from r/{subreddit_name}",
                    leave=False,
                ):
                    post_data = {
                        "id": post.id,
                        "subreddit": subreddit_name,
                        "title": post.title,
                        "selftext": post.selftext,
                        "score": post.score,
                        "upvote_ratio": post.upvote_ratio,
                        "url": post.url,
                        "created_utc": post.created_utc,
                        "num_comments": post.num_comments,
                        "permalink": post.permalink,
                        "comments": self._fetch_comments(
                            post, limit=DEFAULT_COMMENT_LIMIT
                        ),
                    }
                    all_posts.append(post_data)

            except Exception as e:
                logger.error(f"Error searching posts in r/{subreddit_name}: {str(e)}")

        logger.info(
            f"Found {len(all_posts)} posts matching query '{query}' in {len(subreddits)} subreddits"
        )
        return all_posts

    @throttle(min_interval=2.0, key="reddit_comments")
    @with_retry(max_retries=3, base_delay=3.0, backoff_factor=2.0)
    def get_recent_comments(
        self, subreddit: str, since_time: float = None, limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Get recent comments from a subreddit.

        Args:
            subreddit: Subreddit name
            since_time: Unix timestamp to get comments since (default: 1 hour ago)
            limit: Maximum number of comments to fetch (default: 25)

        Returns:
            List of comment dictionaries
        """
        if since_time is None:
            # Default to 1 hour ago
            since_time = time.time() - 3600

        try:
            subreddit_obj = self.reddit.subreddit(subreddit)
            comments = []

            # Log the attempt
            logger.info(f"Fetching up to {limit} recent comments from r/{subreddit}")

            # Process comments in smaller batches to avoid rate limiting
            batch_size = min(limit, 10)  # Process in even smaller batches of 10
            logger.info(f"Processing comments in batches of {batch_size}")

            comment_count = 0
            # Use iterator to fetch comments more efficiently
            comment_iterator = subreddit_obj.comments(limit=limit)

            for comment in comment_iterator:
                # Skip comments older than since_time
                if comment.created_utc < since_time:
                    continue

                comment_count += 1

                try:
                    comment_data = {
                        "id": comment.id,
                        "subreddit": subreddit,
                        "author": str(comment.author),
                        "body": comment.body,
                        "score": comment.score,
                        "created_utc": comment.created_utc,
                        "permalink": comment.permalink,
                        "submission_id": comment.submission.id,
                        "submission_title": comment.submission.title,
                    }
                    comments.append(comment_data)
                except Exception as e:
                    logger.error(f"Error processing comment {comment.id}: {str(e)}")

                # Add a small delay after each batch to avoid rate limiting
                if comment_count % batch_size == 0:
                    logger.info(
                        f"Processed {comment_count} comments, pausing briefly..."
                    )
                    time.sleep(0.5)  # Small delay between batches

            logger.info(
                f"Successfully fetched {len(comments)} comments from r/{subreddit}"
            )
            return comments

        except Exception as e:
            logger.error(f"Error fetching comments from r/{subreddit}: {str(e)}")
            raise

    def reply_to_comment(self, comment_id: str, text: str) -> bool:
        """
        Reply to a comment.

        Args:
            comment_id: ID of the comment to reply to
            text: Text of the reply

        Returns:
            True if the reply was posted successfully, False otherwise
        """
        # Check if we're authenticated and can post
        if not self.is_authenticated or not self.can_post:
            logger.info("Not authenticated for posting. Attempting to authenticate...")
            if not self.authenticate():
                logger.error("Authentication failed. Cannot post comment.")
                return False

        try:
            # Ensure comment_id has the 't1_' prefix that PRAW requires
            if not comment_id.startswith("t1_") and not comment_id.startswith("t3_"):
                # Add t1_ prefix for comments (t3_ is for submissions)
                comment_id = f"t1_{comment_id}"

            logger.info(
                f"Attempting to reply to comment {comment_id} as user {self.username}"
            )

            # Get the comment
            comment = self.reddit.comment(comment_id)

            # Fetch the comment to ensure it exists and is accessible
            try:
                comment.refresh()
                logger.info(
                    f"Successfully fetched comment {comment_id} by u/{comment.author}"
                )
            except Exception as e:
                logger.error(f"Error fetching comment {comment_id}: {str(e)}")
                return False

            # Reply to the comment
            reply = comment.reply(text)

            logger.info(
                f"Successfully replied to comment {comment_id} with ID {reply.id}"
            )
            return True

        except praw.exceptions.RedditAPIException as api_exception:
            for subexception in api_exception.items:
                logger.error(
                    f"Reddit API error: {subexception.error_type} - {subexception.message}"
                )
            return False
        except Exception as e:
            logger.error(f"Error replying to comment {comment_id}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            # Log more details about the error
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
