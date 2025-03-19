import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO)

from dotenv import find_dotenv, load_dotenv

from app.src.reddit_sentiment_analysis.monitoring import RedditMonitor
from app.src.reddit_sentiment_analysis.storage.comment_db import CommentDatabase


async def main():
    print("Starting workflow test...")

    # Create a database connection
    db = CommentDatabase()

    # Get the most recent comment from the database
    import sqlite3

    conn = sqlite3.connect("data/comments.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM comments ORDER BY timestamp DESC LIMIT 1")
    comment_record = dict(cur.fetchone())

    # Delete this comment to force reprocessing
    cur.execute(
        "DELETE FROM comments WHERE comment_id = ?", (comment_record["comment_id"],)
    )
    conn.commit()
    conn.close()

    print(f"Retrieved comment: {comment_record['comment_id']}")
    print(f"Comment text: {comment_record['body']}")

    # Create comment data for processing
    comment = {
        "id": comment_record["comment_id"],
        "author": comment_record["author"],
        "body": comment_record["body"],
        "subreddit": comment_record["subreddit"],
        "permalink": comment_record["permalink"],
        "created_utc": comment_record["created_utc"],
    }

    # Set the monitor recipient email - REPLACE WITH YOUR EMAIL
    recipient_email = "your-email@example.com"  # REPLACE WITH YOUR ACTUAL EMAIL

    # IMPORTANT: Set a test password in the environment
    # NOTE: This is for testing only - in production use the .env file
    # Replace with an actual test password
    old_password = os.environ.get("SENDER_EMAIL_PASSWORD", "")
    os.environ["SENDER_EMAIL_PASSWORD"] = (
        "test_password_123"  # Use a real test password here
    )

    # Print email configuration
    print(f"SMTP_SERVER: {os.getenv('SMTP_SERVER')}")
    print(f"SMTP_PORT: {os.getenv('SMTP_PORT')}")
    print(f"SENDER_EMAIL: {os.getenv('SENDER_EMAIL')}")
    print(
        f"Password set: {bool(os.getenv('SENDER_EMAIL_PASSWORD') and os.getenv('SENDER_EMAIL_PASSWORD') != 'your_password_here')}"
    )

    # Create and initialize the monitor
    monitor = RedditMonitor(
        key_term="ABC Consulting",  # Match the key term that's monitored
        email=recipient_email,
        subreddits=[comment_record["subreddit"]],
        db=db,
    )

    print(f"Created monitor with email: {recipient_email}")

    # Process the comment
    print("Processing comment...")
    result = await monitor.process_comment(comment)

    # Restore original password
    os.environ["SENDER_EMAIL_PASSWORD"] = old_password

    print("Processing complete!")
    print(f"Result: {result}")

    # Check if email was sent
    conn = sqlite3.connect("data/comments.db")
    cur = conn.cursor()
    cur.execute(
        "SELECT email_sent, email_recipient FROM comments WHERE comment_id = ?",
        (comment_record["comment_id"],),
    )
    email_result = cur.fetchone()
    conn.close()

    print(f"Email sent: {bool(email_result[0])}")
    print(f"Email recipient: {email_result[1]}")


if __name__ == "__main__":
    asyncio.run(main())
