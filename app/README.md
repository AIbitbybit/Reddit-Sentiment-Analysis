# Reddit Sentiment Monitoring System

A specialized business monitoring tool that continuously scans Reddit for mentions of your company, product, or brand. It automatically identifies negative comments, sends you immediate email alerts, and suggests professional AI-drafted responses that you can approve with a single click.

## What This Tool Actually Does

The Reddit Sentiment Monitoring System performs these specific functions:

1. **Active Reddit Monitoring**: Scans selected subreddits every 5 minutes for new comments mentioning your key terms.

2. **Sentiment Analysis**: Uses advanced AI (powered by OpenAI) to analyze comment sentiment, classifying each mention as positive, negative, or neutral.

3. **Instant Negative Alerts**: When a negative comment is detected, you immediately receive an email alert containing:

   - The full comment text and context
   - A link to the Reddit post
   - An AI-drafted professional response

4. **One-Click Response**: Reply to the alert email with "Confirmed" to automatically post the suggested response to Reddit.

5. **Historical Analysis**: View and filter historical comments with their sentiment scores in the History tab.

## How It Works

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │    │                 │
│  Reddit Scraper ├───►│ Sentiment Model ├───►│  Email Alerts  ├───►│ Response System │
│                 │    │                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

1. **Collection**: The monitoring system connects to Reddit's API and collects new comments containing your specified key terms from selected subreddits.

2. **Analysis**: Each comment is analyzed by our sentiment engine to determine if it's positive, negative, or neutral, with a confidence score.

3. **Alert**: Negative comments trigger immediate email alerts to your specified address, including the comment and an AI-crafted response.

4. **Response**: You review the suggested response and approve it with a simple email reply; the system then posts it to Reddit on your behalf.

5. **Tracking**: All comments and their sentiment are stored in a database for historical analysis and trend tracking.

## Getting Started

### Prerequisites

- Python 3.11 or newer
- Reddit account with API credentials
- OpenAI API key
- Email account for sending alerts

### Quick Installation

1. Run the installation script for your platform:

   **Windows**:

   ```
   install.bat
   ```

   **macOS/Linux**:

   ```
   ./install.sh
   ```

2. Start the application:

   ```
   python run_app.py
   ```

3. Configure your settings in the application's Settings tab.

### Manual Installation

1. Clone the repository and navigate to the project directory

2. Install dependencies:

   ```
   pip install -e .
   ```

3. Create a `.env` file with your credentials (see `.env.example`)

4. Start the application:
   ```
   python run_app.py
   ```

## Using the Application

### Setting Up Monitoring

1. In the **Monitor** tab:

   - Enter your brand/product name as the key term
   - Enter your email address for alerts
   - Select subreddits to monitor (default: r/business, r/smallbusiness)
   - Click "Start Monitoring"

2. The system will:
   - Run in the background on 5-minute scan intervals
   - Display logs of its activity
   - Show detected comments in real-time
   - Send email alerts only for negative comments

### Responding to Alerts

When you receive an email alert about a negative comment:

1. Review the comment and the suggested AI response
2. If you approve the response, reply to the email with "Confirmed"
3. The system will automatically post the response to the Reddit comment
4. If you don't respond, no action will be taken

### Viewing Historical Data

The **History** tab allows you to:

- View all comments detected by the system
- Filter by sentiment (positive, negative, neutral)
- Search by keyword or date range
- Export data for external analysis

## Configuration Options

### Reddit API Setup

In the Settings tab:

- Enter your Reddit Client ID and Secret
- Configure authentication settings
- Adjust scan frequency (default: 5 minutes)

### Email Settings

In the Settings tab:

- Configure SMTP server details
- Enter sender email credentials
- Test email configuration

### AI Response Settings

In the Settings tab:

- Select OpenAI model (default: gpt-4o)
- Adjust response style preferences
- Configure confidence thresholds

## Email Notifications

The system sends email notifications when negative comments are detected. To configure email notifications:

1. Copy `.env.example` to `.env`
2. Configure the following email settings in your `.env` file:
   - `EMAIL_SMTP_SERVER`: Your SMTP server (default: smtp.gmail.com)
   - `EMAIL_SMTP_PORT`: SMTP port (default: 587)
   - `EMAIL_USERNAME`: Your email username
   - `EMAIL_PASSWORD`: Your email password (use an app-specific password)
   - `EMAIL_RECIPIENT`: Where notifications should be sent
   - `EMAIL_SENDER`: From address for notifications

For Gmail users:

1. Enable 2-factor authentication
2. Generate an app-specific password at https://myaccount.google.com/apppasswords
3. Use this password as your `EMAIL_PASSWORD`

Email notifications include:

- The detected negative comment
- Sentiment analysis results
- Suggested AI response
- A link to the GUI for reviewing and approving responses

## Maintenance

### Database Management

Run the cleanup script to maintain optimal performance:

```
python scripts/cleanup.py --all
```

This script:

- Archives old log files
- Optimizes the database
- Backs up important data
- Clears temporary files

### Regular Maintenance

For best results:

- Archive logs weekly
- Backup the database monthly
- Clear vector database if search performance degrades

## Troubleshooting

### Common Issues

1. **Reddit Authentication Errors**

   - Verify your API credentials in Settings
   - Check that your Reddit app has script permissions

2. **Email Configuration Problems**

   - Test your email settings in the application
   - For Gmail, ensure you're using an App Password with 2FA

3. **Monitoring Not Working**
   - Check your internet connection
   - Verify Reddit API rate limits
   - Ensure subreddits are spelled correctly

## Additional Information

### Data Storage

Comment data is stored in:

- SQLite database (comments.db)
- Vector database for semantic search
- Backed up regularly to the backups/ directory

### Privacy and Security

- Credentials are stored locally in your .env file
- Email alerts contain only public Reddit data
- API keys are never shared or transmitted

## Support and Documentation

For detailed information:

- Email Configuration: See [EMAIL_CONFIG.md](docs/EMAIL_CONFIG.md)
- Project Structure: See [PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)
- Other documentation: Browse the docs/ directory

## License

This project is licensed under the MIT License.

## Acknowledgments

- LangChain and LangGraph for NLP capabilities
- Reddit API for data access
- OpenAI for sentiment analysis and response generation
- Streamlit for the user interface

## Technology Stack

- Python 3.11+
- LangChain for NLP and LLM integration
- OpenAI GPT models for sentiment analysis and response generation
- Streamlit for the web interface
- SQLite for data persistence
- FAISS for efficient similarity search
- Poetry for dependency management

## Response Approval Process

When a negative comment is detected:

1. The system performs sentiment analysis using LangChain and OpenAI
2. An AI-generated response is drafted
3. An email notification is sent to the configured email address
4. The user can review and approve/reject responses in the GUI:
   - Open the application
   - Navigate to the "Pending Responses" tab
   - Review each response
   - Edit if needed
   - Approve or reject
5. Approved responses are automatically posted to Reddit

Note: Previously, responses could be approved via email replies. This functionality has been removed in favor of the more robust GUI-based approval system, which offers better response management and editing capabilities.
