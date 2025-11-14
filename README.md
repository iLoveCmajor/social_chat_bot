# Social Chat Bot 🤖

A Telegram bot that helps people find weekly social partners. The bot sends weekly reminders asking users if they want to be social, then matches participants together by sharing their contact information.

## Features

- 📅 **Weekly Reminders**: Automatically sends reminders at the start of each week
- ✅ **Opt-in/Opt-out System**: Users can choose to participate each week
- 👥 **Participant Matching**: All opted-in users receive a list of others who want to hang out
- 💾 **Persistent Storage**: SQLite database tracks user preferences and weekly participation
- 🔔 **Automated Scheduling**: Uses APScheduler for reliable weekly notifications

## How It Works

1. Users start the bot with `/start` and get registered
2. Every week (configurable day/time), the bot sends a reminder asking if users want to be social
3. Users opt in with `/optin` or opt out with `/optout`
4. At a scheduled time, all opted-in users receive a list of other participants
5. Users can reach out to each other to plan activities

## Installation

### Prerequisites

- Python 3.8 or higher
- A Telegram Bot Token (get one from [@BotFather](https://t.me/botfather))

### Setup

1. Clone the repository:
```bash
git clone https://github.com/iLoveCmajor/social_chat_bot.git
cd social_chat_bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the bot:
   - Copy `config.example.json` to `config.json`
   - Add your bot token from BotFather
   - Optionally customize reminder and matching times

```bash
cp config.example.json config.json
# Edit config.json with your bot token
```

Alternatively, set the bot token as an environment variable:
```bash
export BOT_TOKEN="your_bot_token_here"
```

## Configuration

Edit `config.json` to customize the bot behavior:

```json
{
  "bot_token": "YOUR_BOT_TOKEN_HERE",
  "reminder_day": 0,
  "reminder_time": "09:00",
  "matching_day": 0,
  "matching_time": "12:00"
}
```

**Configuration Options:**
- `bot_token`: Your Telegram bot token (required)
- `reminder_day`: Day of week for reminders (0=Monday, 6=Sunday)
- `reminder_time`: Time to send reminders (24-hour format, e.g., "09:00")
- `matching_day`: Day of week to send participant lists (0=Monday, 6=Sunday)
- `matching_time`: Time to send participant lists (24-hour format, e.g., "12:00")

## Usage

### Running the Bot

```bash
python bot.py
```

The bot will start and listen for commands. Keep it running to maintain scheduled reminders.

### Bot Commands

Once the bot is running, users can interact with it using these commands:

- `/start` - Register with the bot and see welcome message
- `/optin` - Opt in for this week's social matching
- `/optout` - Opt out for this week
- `/status` - Check your current participation status
- `/list` - View all participants for this week
- `/help` - Show help message with all commands

## Example Workflow

1. **Monday 9:00 AM**: Bot sends reminder
   ```
   🔔 Weekly Social Reminder!
   It's a new week (2025-W46)! 🎉
   Would you like to be social this week?
   ```

2. **User Opts In**: User sends `/optin`
   ```
   ✅ Great! You're in for this week!
   I'll send you a list of other participants when the week starts.
   ```

3. **Monday 12:00 PM**: Bot sends participant list to all opted-in users
   ```
   🎊 Your Social Matches for Week 2025-W46!
   Here's everyone who wants to hang out this week:
   1. @alice
   2. @bob
   3. @charlie
   👥 Total: 3 people
   ```

## Database

The bot uses SQLite to store:
- User information (user_id, username, first_name, chat_id)
- Weekly participation records (who opted in/out each week)

Database file: `bot_data.db` (created automatically on first run)

## Development

### Project Structure

```
social_chat_bot/
├── bot.py                    # Main bot implementation
├── requirements.txt          # Python dependencies
├── config.example.json       # Example configuration
├── config.json              # Your configuration (not in git)
├── bot_data.db              # SQLite database (not in git)
├── .gitignore               # Git ignore file
└── README.md                # This file
```

### Running in Production

For production deployment, consider using:
- **systemd** service for Linux servers
- **Docker** for containerized deployment
- **Process managers** like `supervisor` or `pm2`

Example systemd service file:
```ini
[Unit]
Description=Social Chat Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/path/to/social_chat_bot
Environment="BOT_TOKEN=your_token_here"
ExecStart=/usr/bin/python3 /path/to/social_chat_bot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Support

If you encounter any issues or have questions:
1. Check the logs for error messages
2. Verify your bot token is correct
3. Ensure the bot has necessary permissions in your Telegram group
4. Open an issue on GitHub with details about the problem