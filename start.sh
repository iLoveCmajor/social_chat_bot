#!/bin/bash
# Startup script for Social Chat Bot

echo "🤖 Starting Social Chat Bot..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check if config exists
if [ ! -f "config.json" ]; then
    echo "⚠️  Warning: config.json not found!"
    echo "Please create config.json from config.example.json"
    echo "Or set BOT_TOKEN environment variable"
    
    if [ -z "$BOT_TOKEN" ]; then
        echo "❌ BOT_TOKEN not set. Exiting."
        exit 1
    fi
fi

# Run the bot
echo "Starting bot..."
python3 bot.py
