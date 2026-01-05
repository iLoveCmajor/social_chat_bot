#!/bin/bash

# Toggle script for starting/stopping the Telegram bot
BOT_PROCESS=$(pgrep -f "python3 bot.py")

if [ -z "$BOT_PROCESS" ]; then
  echo "🤖 Bot is not running. Starting it..."

  # Display config (hide token for security)
  echo ""
  echo "📋 Configuration:"
  if [ -f "config.json" ]; then
    python3 << 'EOF'
import json
try:
    with open('config.json') as f:
        cfg = json.load(f)
    print(f"  Timezone: {cfg.get('timezone', 'NOT SET')}")
    print(f"  Reminder: days={cfg.get('reminder_days', 'NOT SET')}, time={cfg.get('reminder_time', 'NOT SET')}")
    print(f"  Liking:   days={cfg.get('liking_days', 'NOT SET')}, time={cfg.get('liking_time', 'NOT SET')}")
    print(f"  Matching: days={cfg.get('matching_days', 'NOT SET')}, time={cfg.get('matching_time', 'NOT SET')}")
    print(f"  Admin IDs: {cfg.get('admin_ids', 'NOT SET')}")
except Exception as e:
    print(f"  ⚠️  Error reading config: {e}")
EOF
  else
    echo "  ⚠️  config.json NOT FOUND!"
  fi
  echo ""

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