# Data Directory

This directory contains all data storage for the Reddit Sentiment Analysis application.

## Directory Structure

- `comments.db`: SQLite database containing all monitored comments and their analysis results
- `raw/`: Storage for raw data collected from Reddit
- `vector_db/`: Vector database storage for semantic search functionality

## Database Schema

The `comments.db` file contains the following tables:

### Comments Table

Stores all monitored comments with their sentiment analysis:

| Column          | Type    | Description                                           |
| --------------- | ------- | ----------------------------------------------------- |
| id              | TEXT    | Unique identifier (UUID)                              |
| comment_id      | TEXT    | Reddit comment ID                                     |
| post_id         | TEXT    | Reddit post ID                                        |
| subreddit       | TEXT    | Subreddit name                                        |
| author          | TEXT    | Comment author username                               |
| body            | TEXT    | Comment text content                                  |
| created_utc     | INTEGER | Unix timestamp of comment creation                    |
| permalink       | TEXT    | Reddit permalink to the comment                       |
| sentiment       | TEXT    | Sentiment analysis result (positive/negative/neutral) |
| confidence      | REAL    | Confidence score for sentiment analysis               |
| key_term        | TEXT    | The key term that triggered the monitoring            |
| detected_at     | INTEGER | Unix timestamp of when the comment was detected       |
| ai_response     | TEXT    | Generated AI response for negative comments           |
| response_status | TEXT    | Status of the response (pending/approved/rejected)    |

## Maintenance

- This directory is excluded from version control (via .gitignore)
- Database backups should be created periodically
- The `raw/` and `vector_db/` directories may grow large over time and should be monitored for disk usage
