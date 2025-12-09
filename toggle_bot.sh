#!/bin/bash

# Toggle script for starting/stopping the Telegram bot
BOT_PROCESS=$(pgrep -f "python3 bot.py")

if [ -z "$BOT_PROCESS" ]; then
  echo "🤖 Bot is not running. Starting it..."
  nohup ./start.sh > bot.log 2>&1 &
  echo "✅ Bot started with nohup."
else
  echo "🛑 Bot is running with PID(s): $BOT_PROCESS"
  echo "Stopping..."
  kill $BOT_PROCESS
  echo "✅ Bot stopped."
fi