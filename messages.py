"""Centralized user-facing text for Social Chat Bot."""

TEXT = {
    "welcome": (
        """
        Привет, {first_name}!!
        Это <b>Social Microdosing Bot</b>, инструмент для улучшения твоей социальной жизни.

<b>Идея простая:</b> с людьми видеться хочется, но много об этом думать нет ни времени ни сил.
Этот бот — как раз попытка автоматизировать встречи и упростить планирование.

Как оно работает:
<b>Вторник и четверг — социальные дни.</b>
<b>В понедельник и среду</b> бот спросит, хочешь ли ты увидеться завтра.
После того, как все ответят, ты получишь список тех, кто тоже готов.
Ты можешь оставить список как есть <b>или скрыть тех, с кем пока не хочешь встречаться</b> (об этом никто не узнает).
        Утром в день встречи бот пришлёт твоего мэтча.
        А дальше — договаривайтесь в личке, встречайтес, общайтес!
        """
    ),
    "welcome_yes_response": "Отлично!\nСкоро мы пришлём тебе приглашение на встречи этой недели!",
    "welcome_no_response": "Жаль, но ок(\nВозвращайся, если передумаешь!",
    "change_mind_prompt": "Давай ещё раз)\nЗавтра — день социального микродозинга. Хочешь приесоединиться? Время решиться есть сегодня до 19:00",
    "help": (
        "🤖 Social Chat Bot Buttons:\n\n"
        "• Opt In / Opt Out — control your participation\n"
        "• Dashboard — see who's in and manage dislikes\n"
        "• Status — check whether you're in or out this week\n"
        "• Help — view this message again\n\n"
        "You'll receive weekly reminders to participate!"
    ),
    "optin_confirmation": (
        "Отлично! Скоро мы пришлём тебе приглашение на встречи этой недели!\n\n"
    ),
    "optout_confirmation": (
        "Жаль, но ок( Возвращайся, если передумаешь!\n\n"
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
    "matching_not_opted": "Хорошо, увидимся позже)",
    "matching_participants_header": "Итак, вот список ребят, которые готовы завтра сходить на встречу:",
    "matching_instructions": "Ты можешь оставить его как есть ИЛИ через кнопки ниже отметить тех, с кем завтра не хочешь увидеться (об этом никто не узнает, просто рандомайзер исключит их из твоих мэтчей)",
    "matching_waiting_notice": "Редактировать список можно сегодня <b>до 23:59</b>",
    "matching_no_participants": "Ой, никого нет. Видимо в этот раз микродозинг отменяется.",
    "matching_liked": "➕",
    "matching_disliked": "➖",
    "matching_participant_line": "{idx}. {name} — {state}",
    "matching_no_matches": "Доброе утро!\nВеликий Рандом перемешал пары, но тебе, к сожалению, не хватило партнера( Возможно на сегодня отметилось слишком мало людей.\nМожет быть это повод проявить активность и самому написать кому-то? Или хороший день, чтобы провести время с собой?\nМы скоро вернёмся с приглашением на следующие встречи, stay tuned!",
    "matching_pair_announcement": "Доброе утро!Сегодня социальный день, и в этот раз твой мэтч — {name}. Самое время написать друг другу и договориться о встрече — позавтракать вместе, выйти на прогулку, поковоркать, it's up to you.Хорошего дня)",
    "matching_opted_in_waiting": "✅ Супер, ты в списках! Подождём немного ответов других участников и в <b>19:00</b>  пришлём список тех, кто готов ко встрече",
    "unknown_user": "Unknown",
    "weekly_reminder": (
        "Привет, {first_name}!\n\n"
        "Завтра — день социального микродозинга. Хочешь приесоединиться?\n\n"
        "Время решиться есть сегодня до 19:00."
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
    "liking_phase_already_in": "Liking phase is underway and you're already participating. Use the buttons to manage dislikes or tap Dislike Everyone to avoid matches.",
}

BUTTONS = {
    "unlike": "❌ Скрыть {name}",
    "like": "🔄 Вернуть {name}",
    "optin": "✅ Да, погнали",
    "optout": "⏭ Не в этот раз",
    "optout_final": "🙅 Скрыть всех",
    "intro_yes": "Окей, я в деле",
    "intro_no": "Не, я пас",
    "change_mind": "Ой, я передумал!",
}

RESPONSES = {
    "like_success": "Liked!",
    "dislike_success": "Marked as disliked.",
    "dislike_removed": "Removed dislike.",
    "optin_set": "You're in for this week!",
    "optout_set": "You're out for this week.",
    "dislike_all_set": "You won't be matched this week.",
    "unknown": "Unknown action.",
    "done": "Done.",
}

ALERTS = {
    "like_requires_optin": "Both users must be opted in before liking.",
    "dislike_failed": "Could not update dislike.",
    "matching_locked": "Matching is already in progress this week. Likes are closed.",
    "liking_locked": "Preference changes are only available during the liking phase.",
    "optin_phase_only": "А всё, а раньше надо было!\nРегистрация на завтра закрыта, увидимся в следующий раз!",
}
