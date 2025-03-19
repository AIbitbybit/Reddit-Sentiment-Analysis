@echo off
echo Reddit Sentiment Analysis - Installation Script
echo This script will install the required dependencies for the Reddit Sentiment Analysis tool.
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher and try again.
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%I in ('python --version 2^>^&1') do set PYTHON_VERSION=%%I
echo Python %PYTHON_VERSION% detected.

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -e .

REM Check if .env file exists
if not exist ".env" (
    echo Warning: .env file not found. Creating from template...
    if exist ".env.example" (
        copy .env.example .env
        echo Created .env file. Please edit .env with your credentials.
        echo You can also configure all settings directly in the application's Settings tab.
    ) else (
        echo Error: Could not find .env.example template.
    )
)

echo.
echo Installation completed successfully!
echo To run the application, use the following command:
echo venv\Scripts\activate.bat ^&^& python run_app.py
echo You can configure all settings in the Settings tab of the application.
echo.
echo Thank you for using Reddit Sentiment Analysis!

pause 
