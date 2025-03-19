#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Reddit Sentiment Analysis - Installation Script${NC}"
echo "This script will install the required dependencies for the Reddit Sentiment Analysis tool."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed.${NC}"
    echo "Please install Python 3 and try again."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python version $PYTHON_VERSION is not supported.${NC}"
    echo "Please install Python $REQUIRED_VERSION or higher and try again."
    exit 1
fi

echo -e "${GREEN}Python $PYTHON_VERSION detected.${NC}"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -e .

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from template...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}Created .env file. Please edit .env with your credentials.${NC}"
        echo -e "${GREEN}You can also configure all settings directly in the application's Settings tab.${NC}"
    else
        echo -e "${RED}Error: Could not find .env.example template.${NC}"
    fi
fi

echo -e "${GREEN}Installation completed successfully!${NC}"
echo "To run the application, use the following command:"
echo -e "${YELLOW}source venv/bin/activate && python run_app.py${NC}"
echo -e "You can configure all settings in the Settings tab of the application."
echo -e "${GREEN}Thank you for using Reddit Sentiment Analysis!${NC}" 
