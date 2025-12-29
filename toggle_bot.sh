#!/bin/bash

# Toggle script for starting/stopping the Telegram bot
BOT_PROCESS=$(pgrep -f "python3 bot.py")

if [ -z "$BOT_PROCESS" ]; then
  echo "🤖 Bot is not running. Starting it..."
  TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
  LOG_FILE="bot_${TIMESTAMP}.log"
  nohup ./start.sh > "$LOG_FILE" 2>&1 &
  echo "✅ Bot started with nohup."
  echo "📝 Logs: $LOG_FILE"
  echo "📖 View logs: tail -f $LOG_FILE"
  # Also create/update a symlink to the latest log
  ln -sf "$LOG_FILE" bot_latest.log
else
  echo "🛑 Bot is running with PID(s): $BOT_PROCESS"
  echo "Stopping..."
  kill $BOT_PROCESS
  echo "✅ Bot stopped."
fi