# Usage Examples

## Initial Setup

1. Get your bot token from [@BotFather](https://t.me/botfather):
   - Send `/newbot` to BotFather
   - Choose a name and username for your bot
   - Copy the token provided

2. Configure the bot:
```bash
cp config.example.json config.json
# Edit config.json and paste your bot token
```

Or use environment variable:
```bash
export BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
```

3. Run the bot:
```bash
./start.sh
```

## User Interaction Examples

### Example 1: First-time User

User starts bot:
```
User: /start

Bot: 👋 Hello Alice!

Welcome to the Social Chat Bot! 🎉

This bot helps you find people to hang out with each week.

📅 How it works:
• Every week, I'll ask if you want to be social
• If you opt in, you'll get a list of others who also want to hang out
• Connect with them and have fun!

Commands:
/optin - Opt in for this week's social matching
/optout - Opt out for this week
/status - Check your current status
/list - See who's available this week
/help - Show this message again
```

### Example 2: Opting In

User opts in for the week:
```
User: /optin

Bot: ✅ Great! You're in for this week!

I'll send you a list of other participants when the week starts.
Use /list to see who's already signed up.
```

### Example 3: Checking Status

User checks their participation status:
```
User: /status

Bot: 📊 Your Status (Week 2025-W46):

✅ You're IN for this week's social matching!

Use /optin or /optout to change your status.
```

### Example 4: Viewing Current Participants

User views who's participating:
```
User: /list

Bot: 🎉 People available to hang out this week (2025-W46):

1. @alice
2. @bob
3. @charlie
4. @diana

👥 Total: 4 people

Reach out to them and plan something fun!
```

### Example 5: Opting Out

User decides to opt out:
```
User: /optout

Bot: 👋 No problem! You've opted out for this week.

You can use /optin anytime to join again!
```

## Automated Weekly Flow

### Monday 9:00 AM - Weekly Reminder

Bot sends to all users:
```
🔔 Weekly Social Reminder!

It's a new week (2025-W46)! 🎉

Would you like to be social this week?

If yes, use /optin to join!
You'll get a list of others who want to hang out too.

Commands:
/optin - I want to be social! ✅
/optout - Not this week ❌
/list - See who's already signed up
```

### Monday 12:00 PM - Participant List Distribution

Bot sends to all opted-in users:
```
🎊 Your Social Matches for Week 2025-W46!

Here's everyone who wants to hang out this week:

1. @alice
2. @bob
3. @charlie
4. @diana
5. @eve

👥 Total: 5 people

Reach out and plan something fun! 🎉
Have a great week! 😊
```

## Configuration Examples

### Example 1: Reminder on Sunday Evening, Matches on Monday Morning

```json
{
  "bot_token": "YOUR_TOKEN",
  "reminder_day": 6,
  "reminder_time": "18:00",
  "matching_day": 0,
  "matching_time": "08:00"
}
```

### Example 2: Both on Monday Morning

```json
{
  "bot_token": "YOUR_TOKEN",
  "reminder_day": 0,
  "reminder_time": "09:00",
  "matching_day": 0,
  "matching_time": "12:00"
}
```

### Example 3: Reminder on Friday, Matches on Saturday

```json
{
  "bot_token": "YOUR_TOKEN",
  "reminder_day": 4,
  "reminder_time": "17:00",
  "matching_day": 5,
  "matching_time": "10:00"
}
```

Note: Days are numbered 0-6, where 0=Monday, 1=Tuesday, ..., 6=Sunday.
