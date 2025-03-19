import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from app.src.reddit_sentiment_analysis.email_service import EmailService


async def main():
    print("Starting email test...")
    email_service = EmailService()

    # Get the most recent comment from the database
    import sqlite3

    conn = sqlite3.connect("data/comments.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM comments ORDER BY timestamp DESC LIMIT 1")
    comment = dict(cur.fetchone())
    conn.close()

    print(f"Testing email for comment: {comment['comment_id']}")
    print(f"Sentiment: {comment['sentiment']}")
    print(f"Email service configuration:")
    print(f"SMTP Server: {email_service.smtp_server}")
    print(f"SMTP Port: {email_service.smtp_port}")
    print(f"Sender Email: {email_service.sender_email}")
    print(
        f"Password configured: {bool(email_service.sender_password and email_service.sender_password != 'your_password_here')}"
    )

    # Construct test data
    comment_data = {
        "id": comment["comment_id"],
        "author": comment["author"],
        "body": comment["body"],
        "subreddit": comment["subreddit"],
        "permalink": comment["permalink"],
    }

    sentiment_result = {
        "sentiment": comment["sentiment"],
        "confidence": comment["confidence"],
    }

    # Try to send email - use your actual email here
    recipient = "your-email@example.com"  # REPLACE WITH YOUR ACTUAL EMAIL
    print(f"Attempting to send email to {recipient}...")

    try:
        result = await email_service.send_alert(
            recipient=recipient,
            comment_data=comment_data,
            sentiment_result=sentiment_result,
            suggested_response=comment["ai_response"],
        )

        print(f"Email send result: {result}")
    except Exception as e:
        print(f"Exception during email sending: {e}")
        import traceback

        print(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())
