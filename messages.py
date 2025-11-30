"""Centralized user-facing text for Social Chat Bot."""

TEXT = {
    "welcome": (
        "👋 Hello {first_name}!\n\n"
        "Welcome to the Social Chat Bot! 🎉\n\n"
        "This bot helps you find people to hang out with each week.\n\n"
        "📅 How it works:\n"
        "• Every week, I'll ask if you want to be social\n"
        "• If you opt in, you'll get a list of others who also want to hang out\n"
        "• Connect with them and have fun!\n\n"
        "Commands:\n"
        "/optin - Opt in for this week's social matching\n"
        "/optout - Opt out for this week\n"
        "/status - Check your current status\n"
        "/list - See who's available this week\n"
        "/help - Show this message again"
    ),
    "help": (
        "🤖 Social Chat Bot Commands:\n\n"
        "/start - Start the bot and register\n"
        "/optin - Opt in for this week's social matching\n"
        "/optout - Opt out for this week\n"
        "/status - Check your current participation status\n"
        "/list - See who's available to hang out this week\n"
        "/help - Show this help message\n\n"
        "You'll receive weekly reminders to participate!"
    ),
    "optin_confirmation": (
        "✅ Great! You're in for this week!\n\n"
        "I'll send you a list of other participants when the week starts.\n"
        "Use /list to see who's already signed up."
    ),
    "optout_confirmation": (
        "👋 No problem! You've opted out for this week.\n\n"
        "You can use /optin anytime to join again!"
    ),
    "status_in": "✅ You're IN for this week's social matching!",
    "status_out": "❌ You're currently opted out for this week.",
    "status_summary": (
        "📊 Your Status ({week_label}):\n\n"
        "{status}\n\n"
        "Use /optin or /optout to change your status."
    ),
    "matching_phase_title": "🎯 Matching Phase ({week_label})",
    "matching_not_opted": (
        "You're currently not opted in for this week. Use /optin to join the matching phase."
    ),
    "matching_instructions": "Everyone starts liked. Tap 💔 to remove someone or ❤️ to add them back before matching begins.",
    "matching_participants_header": "👥 Opted-in participants:",
    "matching_no_participants": "- No other participants yet. Invite friends to opt in!",
    "matching_liked": "❤️ Interested",
    "matching_disliked": "💔 Disliked",
    "matching_not_liked": "♡ Pending",
    "matching_participant_line": "{idx}. {name} — {state}",
    "matching_matches_header": "💌 Your matches:",
    "matching_no_matches": "Sorry, no match this week.",
    "matching_waiting_notice": "Matching hasn't started yet. Keep liking people you're interested in!",
    "matching_phase_locked": "✨ Matching for this week has started. Likes are frozen and your final match is below.",
    "matching_match_line": "{idx}. {you_label} ❤️ {name}",
    "matching_you_label": "You",
    "unknown_user": "Unknown",
    "weekly_reminder": (
        "🔔 Weekly Social Reminder!\n\n"
        "It's a new week ({week_label})! 🎉\n\n"
        "Would you like to be social this week?\n\n"
        "If yes, use /optin to join!\n"
        "You'll get a list of others who want to hang out too.\n\n"
        "Commands:\n"
        "/optin - I want to be social! ✅\n"
        "/optout - Not this week ❌\n"
        "/list - See who's already signed up"
    ),
    "admin_only": "⛔ This command is restricted to admins.",
    "admin_optin_sent": "✅ Weekly reminder sent to {count} active users.",
    "admin_optin_none": "⚠️ No active users found to notify.",
    "admin_matching_sent": "📬 Participant list sent to {count} opted-in users.",
    "admin_matching_none": "ℹ️ There are no participants to send a list to this week.",
    "admin_reset": "🔄 Cleared {count} participation record(s) for week {week_label}.",
    "admin_status": (
        "📊 Weekly Status ({week_label}):\n"
        "• Active users: {active}\n"
        "• Opted in: {opted_in}\n"
        "• Opted out: {opted_out}\n"
        "• No response yet: {pending}"
    ),
}

BUTTONS = {
    "unlike": "💔 Dislike {name}",
    "like": "❤️ Undo dislike for {name}",
    "like_all": "❤️ Like everyone",
    "refresh": "Refresh 🔄",
}

RESPONSES = {
    "like_success": "Liked!",
    "dislike_success": "Marked as disliked.",
    "dislike_removed": "Removed dislike.",
    "like_all_success": "Liked everyone!",
    "refresh": "Lists refreshed.",
    "unknown": "Unknown action.",
    "done": "Done.",
}

ALERTS = {
    "like_requires_optin": "Both users must be opted in before liking.",
    "dislike_failed": "Could not update dislike.",
    "like_all_unavailable": "No participants to like or you're not opted in.",
    "matching_locked": "Matching is already in progress this week. Likes are closed.",
}
