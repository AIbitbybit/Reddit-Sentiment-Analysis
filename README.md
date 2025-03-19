# Reddit Sentiment Analysis

An automated system for monitoring and responding to Reddit comments, with sentiment analysis and human-in-the-loop approval.

## Features

- **Sentiment Analysis**: Analyze the sentiment of Reddit comments using OpenAI GPT models
- **Response Generation**: Automatically generate response drafts for negative comments
- **Human Approval**: Approve or modify AI-generated responses before posting
- **Email Alerts**: Get notified about important comments via email
- **Database Storage**: Store all comments and their analysis results
- **Permalink Validation**: Ensure all Reddit links are properly formatted for reference

## Application Structure

```
app/
├── src/
│   └── reddit_sentiment_analysis/
│       ├── analysis/            # Sentiment analysis components
│       ├── config/              # Configuration management
│       ├── integrations/        # Integration with external services
│       ├── monitoring/          # Reddit monitoring and email alerts
│       ├── preprocessing/       # Text processing utilities
│       ├── storage/             # Database management
│       └── workflows/           # LangGraph workflows
├── tests/
│   ├── integration/             # Integration tests
│   └── unit/                    # Unit tests
└── test_basic_functions.py      # Basic functionality tests
```

## Testing

The application includes several test suites:

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test how components work together
3. **Basic Functionality Tests**: Test core application features

To run the basic functionality tests:

```bash
python app/test_basic_functions.py
```

## Key Components

### Sentiment Analyzer

Uses OpenAI's models to analyze the sentiment of comments and classify them as positive, negative, or neutral.

### Workflow System

The application uses LangGraph for workflow management, allowing for a structured process of:

1. Analyzing comment sentiment
2. Generating responses for negative comments
3. Human review and approval
4. Storing results

### Database

SQLite database for storing:

- Comment details
- Sentiment analysis results
- Generated responses
- Approval status
- Email notification status

### Email Service

Sends email alerts for negative comments that require attention, including:

- Comment details
- Sentiment analysis
- Link to the original Reddit comment
- Generated response draft

## Setting Up

1. Set up environment variables (see `.env.example`)

   - Configure email settings:
     ```
     SMTP_SERVER=smtp.example.com
     SMTP_PORT=587
     SENDER_EMAIL=your_email@example.com
     SENDER_EMAIL_PASSWORD=your_password_here
     EMAIL_SKIP_VERIFY=false  # Set to "true" only for testing with self-signed certificates
     ```
   - Set OpenAI API key:
     ```
     OPENAI_API_KEY=your_openai_api_key
     OPENAI_MODEL=gpt-4o
     ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app/src/reddit_sentiment_analysis/monitoring/monitoring.py
   ```

### Email Service SSL Certificate Verification

By default, the email service will verify SSL certificates for secure SMTP connections. When using self-signed certificates for testing, you can set `EMAIL_SKIP_VERIFY=true` in your `.env` file to bypass certificate verification.

**Warning**: Disabling SSL certificate verification is not recommended for production use as it makes the connection insecure.

## Extending the Application

The application can be extended with:

- Additional sentiment analysis models
- Support for more social media platforms
- Advanced response generation strategies
- Dashboard for managing responses
