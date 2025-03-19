# Email Configuration Guide

This guide will help you set up email notifications for the Reddit Sentiment Analysis application.

## Configuration Options

The application requires SMTP settings to send email notifications. These settings can be configured in two ways:

1. Through the Settings tab in the application GUI
2. By manually editing the `.env` file

## Required Settings

The following settings are required for email functionality:

| Setting       | Description                         | Example                          |
| ------------- | ----------------------------------- | -------------------------------- |
| SMTP_SERVER   | SMTP server address                 | smtp.gmail.com                   |
| SMTP_PORT     | SMTP server port                    | 587                              |
| SMTP_USERNAME | Your email address                  | your.email@gmail.com             |
| SMTP_PASSWORD | Your email password or app password | abcdefghijklmnop                 |
| EMAIL_FROM    | The "From" address for sent emails  | Your Name <your.email@gmail.com> |

## Provider-Specific Configuration

### Gmail

For Gmail, you'll need to use an "App Password" if you have 2-Factor Authentication enabled:

1. Go to your Google Account settings (https://myaccount.google.com/)
2. Select "Security"
3. Under "Signing in to Google," select "App passwords"
   (If you don't see this option, 2-Step Verification is not enabled for your account)
4. Select "Mail" as the app and "Other" as the device
5. Enter "Reddit Sentiment Analysis" as the name
6. Google will generate a 16-character password - use this as your SMTP_PASSWORD

**Settings for Gmail:**

```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your.gmail.address@gmail.com
SMTP_PASSWORD=your-app-password
```

### Outlook/Office 365

For Outlook or Office 365:

```
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=your.email@outlook.com
SMTP_PASSWORD=your-password
```

### Yahoo Mail

For Yahoo Mail:

```
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USERNAME=your.email@yahoo.com
SMTP_PASSWORD=your-password
```

### Hostinger

For Hostinger email:

```
SMTP_SERVER=smtp.hostinger.com
SMTP_PORT=587
SMTP_USERNAME=your.email@yourdomain.com
SMTP_PASSWORD=your-password
```

## Testing Your Configuration

You can test your email configuration using the email debug script:

```
python scripts/email_debug.py
```

This script will:

1. Load your email configuration from the `.env` file
2. Attempt to connect to the SMTP server
3. Send a test email to the address you specify

## Troubleshooting

### Common Issues

1. **Authentication Failed**

   - Double-check your username and password
   - For Gmail, ensure you're using an App Password if 2FA is enabled
   - Verify that your email provider allows SMTP access for your account type

2. **Connection Refused**

   - Check if your SMTP server and port are correct
   - Your ISP might be blocking outgoing SMTP connections
   - Try changing to port 465 with SSL/TLS if port 587 doesn't work

3. **Timeout Error**
   - Your network might be blocking the connection
   - Check your firewall settings
   - Try using a different network

### Secure Storage

The application stores your email credentials in the `.env` file. This file should be kept secure and never committed to version control. The application includes a `.env.example` file that demonstrates the structure without containing sensitive information.
