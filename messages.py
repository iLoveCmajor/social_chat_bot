"""Centralized user-facing text for Social Chat Bot."""

TEXT = {
    "welcome": (
        "👋 Hello {first_name}!\n\n"
        "Welcome to the Social Chat Bot! 🎉\n\n"
        "This bot helps you find people to hang out with each week.\n\n"
        "📅 How it works:\n"
        "• Every week, I'll ask if you want to be social\n"
        "• Opt in to join this week's pool\n"
        "• Use the dashboard to review participants and mark dislikes\n"
        "• You'll get a final match once the matching phase begins\n\n"
        "Use the buttons below to control everything."
    ),
    "help": (
        "🤖 Social Chat Bot Buttons:\n\n"
        "• Opt In / Opt Out — control your participation\n"
        "• Dashboard — see who's in and manage dislikes\n"
        "• Status — check whether you're in or out this week\n"
        "• Help — view this message again\n\n"
        "You'll receive weekly reminders to participate!"
    ),
    "optin_confirmation": (
        "✅ Great! You're in for this week!\n\n"
        "Everyone starts liked by default—use the buttons below to mark anyone you don't want to match with."
    ),
    "optout_confirmation": (
        "👋 No problem! You've opted out for this week.\n\n"
        "Use the Opt In button anytime to join again!"
    ),
    "status_in": "✅ You're IN for this week's social matching!",
    "status_out": "❌ You're currently opted out for this week.",
    "status_summary": (
        "📊 Your Status ({week_label}):\n\n"
        "{status}\n\n"
        "Use the Opt In/Opt Out buttons to change your status."
    ),
    "matching_phase_change_locked_optedin": (
        "⚠️ Matching for this week is already in progress, so changes are locked.\n"
        "Here's your current match view:"
    ),
    "matching_phase_change_locked_notoptedin": (
        "⚠️ Matching for this week has already started and changes are locked.\n"
        "You weren't part of this week's pool—please come back next week!"
    ),
    "matching_phase_title": "🎯 Matching Phase ({week_label})",
    "matching_not_opted": (
        "You're currently not opted in for this week. Tap the Opt In button below to join."
    ),
    "matching_instructions": "Everyone starts liked. Tap 💔 to remove someone or ❤️ to add them back before matching begins.",
    "optin_phase_instructions": "We're currently collecting opt-ins. Use the Opt In/Opt Out buttons to update your status for this week.",
    "matching_participants_header": "👥 Opted-in participants:",
    "matching_no_participants": "- No other participants yet. Invite friends to opt in!",
    "matching_liked": "❤️ Interested",
    "matching_disliked": "💔 Disliked",
    "matching_not_liked": "♡ Pending",
    "matching_participant_line": "{idx}. {name} — {state}",
    "matching_matches_header": "💌 Matches",
    "matching_no_matches": "Sorry, no match this week.",
    "matching_waiting_notice": "Matching hasn't started yet. Keep reviewing your preferences.",
    "optin_phase_waiting_notice": "Liking opens soon. You'll be able to manage dislikes in the next phase.",
    "matching_phase_locked": "✨ Matching for this week has started. Likes are frozen and your final match is below.",
    "matching_match_line": "{idx}. {you_label} ❤️ {name}",
    "matching_you_label": "You",
    "unknown_user": "Unknown",
    "weekly_reminder": (
        "🔔 Weekly Social Reminder!\n\n"
        "It's a new week ({week_label})! 🎉\n\n"
        "Would you like to be social this week?\n\n"
        "Tap Opt In if you're available or Opt Out if you're busy.\n"
        "Use the Dashboard button to see who else has joined."
    ),
    "admin_only": "⛔ This command is restricted to admins.",
    "admin_next_phase_liking_sent": "🎬 Liking phase started and sent dashboards to {count} participants.",
    "admin_next_phase_matching_sent": "🚀 Matching phase started and sent dashboards to {count} participants.",
    "admin_next_phase_none": "ℹ️ No opted-in participants to move forward yet.",
    "admin_next_phase_blocked": "⚠️ Matching is already active. Use /admin_reset to restart the cycle.",
    "admin_reset": "🔄 Restarted {week_label}: cleared {count} participation record(s) and sent reminders to {notified} active user(s).",
    "admin_status": (
        "📊 Weekly Status ({week_label}):\n"
        "• Active users: {active}\n"
        "• Opted in: {opted_in}\n"
        "• Opted out: {opted_out}\n"
        "• No response yet: {pending}"
    ),
    "admin_pairs_header": "🤝 Matches for {week_label}:",
    "admin_pairs_line": "{idx}. {name_a} ❤️ {name_b}",
    "admin_pairs_none": "🤝 No mutual matches were created this week.",
    "admin_list_optin_header": "📝 Opt-in overview for {week_label}:",
    "admin_list_participant_line": "• {name}\n  Likes: {likes}\n  Dislikes: {dislikes}",
    "admin_list_none": "None",
    "admin_list_no_participants": "ℹ️ No opted-in participants for {week_label}.",
    "admin_list_unmatched_header": "🙋 Unmatched participants:",
    "admin_list_unmatched_line": "• {name}",
    "admin_list_unmatched_none": "Everyone received a match this week!",
    "liking_phase_optin_closed": "Opt-ins are closed while the liking phase is in progress. Please come back next week!",
    "liking_phase_already_in": "Liking phase is underway and you're already participating. Use the dashboard to manage dislikes or tap Opt Out to leave.",
}

BUTTONS = {
    "unlike": "💔 Dislike {name}",
    "like": "❤️ Like {name}",
    "optin": "✅ Opt me in",
    "optout": "🚫 Opt me out",
    "optout_final": "🚫 Opt me out (irreversible)",
    "dashboard": "📋 Dashboard",
    "status": "📊 Status",
    "help": "❓ Help",
    "refresh": "Refresh 🔄",
}

RESPONSES = {
    "like_success": "Liked!",
    "dislike_success": "Marked as disliked.",
    "dislike_removed": "Removed dislike.",
    "optin_set": "You're in for this week!",
    "optout_set": "You're out for this week.",
    "refresh": "Lists refreshed.",
    "unknown": "Unknown action.",
    "done": "Done.",
}

ALERTS = {
    "like_requires_optin": "Both users must be opted in before liking.",
    "dislike_failed": "Could not update dislike.",
    "matching_locked": "Matching is already in progress this week. Likes are closed.",
    "liking_locked": "Preference changes are only available during the liking phase.",
    "optin_phase_only": "Opt-in controls are only available during the opt-in phase.",
}
