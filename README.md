# Social Chat Bot 🤖

A Telegram bot that helps people find weekly social partners. The bot sends weekly reminders asking users if they want to be social, then matches participants together by sharing their contact information.

📖 **Documentation:** [Usage Examples](USAGE.md) | [Contributing Guide](CONTRIBUTING.md)

## Features

- 📅 **Weekly Reminders**: Automatically sends reminders at the start of each week
- ✅ **Opt-in/Opt-out System**: Users can choose to participate each week
- 👥 **Participant Matching**: All opted-in users receive a list of others who want to hang out
- 💘 **Mutual Likes & Matches**: Like other participants during the opt-in phase, then receive curated matches once the matching phase begins
- 💾 **Persistent Storage**: SQLite database tracks user preferences and weekly participation
- 🔔 **Automated Scheduling**: Uses APScheduler for reliable weekly notifications
- 🛡️ **Admin Controls**: Manually trigger reminders, matching, reset weeks, and monitor status

## How It Works

1. Users start the bot with `/start` and get registered
2. Every week (configurable day/time), the bot sends a reminder asking if users want to be social
3. Users opt in with `/optin` or opt out with `/optout`
4. Admins advance the process through three phases:
   - **Opt-in phase** – people can only /optin or /optout and view the roster
   - **Liking phase** – the roster locks, everyone begins liked by default, and participants can dislike specific people
   - **Matching phase** – likes freeze and each person sees their final match (or a “no match” notice)
5. Users can reach out to each other to plan activities once matches are announced

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

### Quick Start with Script

Use the provided startup script:
```bash
./start.sh
```

### Docker Deployment

Using Docker Compose (recommended):
```bash
# Set your bot token
export BOT_TOKEN="your_bot_token_here"

# Start the bot
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the bot
docker-compose down
```

Using Docker directly:
```bash
# Build the image
docker build -t social-chat-bot .

# Run the container
docker run -d --name social-chat-bot \
  -e BOT_TOKEN="your_bot_token_here" \
  -v $(pwd)/bot_data.db:/app/bot_data.db \
  social-chat-bot
```

## Configuration

Edit `config.json` to customize the bot behavior:

```json
{
  "bot_token": "YOUR_BOT_TOKEN_HERE",
  "reminder_day": 0,
  "reminder_time": "09:00",
  "liking_day": 0,
  "liking_time": "11:00",
  "matching_day": 0,
  "matching_time": "12:00",
  "admin_ids": [
    123456789
  ]
}
```

**Configuration Options:**
- `bot_token`: Your Telegram bot token (required)
- `reminder_day`: Day of week for reminders (0=Monday, 6=Sunday)
- `reminder_time`: Time to send reminders (24-hour format, e.g., "09:00")
- `liking_day`: Day of week for the liking-phase broadcast (0=Monday, 6=Sunday)
- `liking_time`: Time to send the liking-phase dashboards (24-hour format, e.g., "11:00")
- `matching_day`: Day of week to send participant lists (0=Monday, 6=Sunday)
- `matching_time`: Time to send participant lists (24-hour format, e.g., "12:00")
- `admin_ids`: List of Telegram user IDs allowed to use admin commands (optional). You can also set the `ADMIN_IDS` env var with a comma-separated list, e.g., `export ADMIN_IDS="111,222"`.

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
- `/list` - Open the matching dashboard: everyone starts liked, so tap 💔 to remove someone (or ❤️ to undo) before matching begins, then view your finalized match once the matching phase begins
- `/help` - Show help message with all commands

**Admin Commands** (restricted to IDs in `admin_ids` / `ADMIN_IDS`):

- `/admin_next_phase` - Advance to the next phase (opt-in ➜ liking ➜ matching); if matching is already active, it tells you to reset instead
- `/admin_list` - Show a full overview: during opt-in see each participant with their likes/dislikes, during matching see all matches and anyone still unmatched
- `/admin_status` - See how many users are active/opted-in/opted-out for the current week
- `/admin_reset` - Reset the current week and send a fresh opt-in reminder to everyone

## Example Workflow

1. **Monday 9:00 AM**: Bot sends reminder
   ```
   🔔 Weekly Social Reminder!
   It's a new week (06/01/2025 - 12/01/2025)! 🎉
   Would you like to be social this week?
   ```

2. **User Opts In**: User sends `/optin`
   ```
   ✅ Great! You're in for this week!
   I'll send you a list of other participants when the week starts.
   ```

3. **Monday 12:00 PM**: Bot sends the matching dashboard to all opted-in users
   ```
   🎯 Matching Phase (06/01/2025 - 12/01/2025)
   Everyone starts liked. Tap 💔 to remove someone or ❤️ to bring them back before matching closes.
   👥 Opted-in participants:
   1. @alice — ❤️ Interested
   2. @bob — 💔 Disliked

   💌 Your matches:
   1. You ❤️ @alice
   ```

## Database

The bot uses SQLite to store:
- User information (user_id, username, first_name, chat_id)
- Weekly participation records (who opted in/out each week)
- Weekly state flags (tracks when the matching phase has started)
- Weekly likes/dislikes to determine mutual matches

Database file: `bot_data.db` (created automatically on first run)

## Development

### Project Structure

```
social_chat_bot/
├── bot.py                    # Main bot implementation
├── test_bot.py              # Test suite for bot functionality
├── requirements.txt          # Python dependencies
├── config.example.json       # Example configuration
├── config.json              # Your configuration (not in git)
├── .env.example             # Example environment variables
├── start.sh                 # Startup script
├── Dockerfile               # Docker container definition
├── docker-compose.yml       # Docker Compose configuration
├── bot_data.db              # SQLite database (not in git)
├── README.md                # This file
├── USAGE.md                 # Detailed usage examples
├── CONTRIBUTING.md          # Contributing guidelines
├── LICENSE                  # MIT License
└── .gitignore               # Git ignore file
```

### Testing

Run the test suite to verify functionality:
```bash
python3 test_bot.py
```

The test suite validates:
- Database initialization
- User management operations
- Participation tracking
- Data retrieval functions


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

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is open source and available under the [MIT License](LICENSE).

## Support

If you encounter any issues or have questions:
1. Check the [Usage Examples](USAGE.md) for common scenarios
2. Check the logs for error messages
3. Verify your bot token is correct
4. Ensure the bot has necessary permissions in your Telegram group
5. Open an issue on GitHub with details about the problem
