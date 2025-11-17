#!/usr/bin/env python3
"""
Social Chat Bot - Weekly Social Matching Bot for Telegram
Helps people find partners to hang out by matching weekly participants.
"""

import os
import json
import logging
from datetime import datetime, time
from typing import Dict, Set, List, Optional
import sqlite3
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def _parse_admin_ids(value) -> List[int]:
    """Parse admin IDs from config/env inputs."""
    if value is None:
        return []
    
    if isinstance(value, str):
        raw_values = [item.strip() for item in value.split(',')]
    elif isinstance(value, (list, tuple, set)):
        raw_values = value
    else:
        raw_values = [value]
    
    admin_ids = []
    for item in raw_values:
        if item in ("", None):
            continue
        try:
            admin_ids.append(int(item))
        except (TypeError, ValueError):
            logger.warning("Ignoring invalid ADMIN_IDS entry: %s", item)
    
    return admin_ids


class SocialChatBot:
    """Main bot class for handling social matching functionality."""
    
    def __init__(self, bot_token: str, config: dict):
        self.bot_token = bot_token
        self.config = config
        self.db_path = Path(__file__).parent / "bot_data.db"
        self.scheduler = AsyncIOScheduler()
        self.application = None
        self.admin_ids: Set[int] = set(config.get('admin_ids', []))
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for storing user data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                chat_id INTEGER,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Create weekly participation table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_participation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                week_year TEXT,
                opted_in INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_busy INTEGER DEFAULT 0,
                UNIQUE(user_id, week_year)
            )
        ''')

        # Ensure legacy databases have the is_busy column
        cursor.execute("PRAGMA table_info(weekly_participation)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'is_busy' not in columns:
            cursor.execute('ALTER TABLE weekly_participation ADD COLUMN is_busy INTEGER DEFAULT 0')

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def _get_current_week(self) -> str:
        """Get current week identifier (year-week)."""
        now = datetime.now()
        return f"{now.year}-W{now.isocalendar()[1]:02d}"
    
    def _add_user(self, user_id: int, username: str, first_name: str, chat_id: int):
        """Add or update user in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, chat_id, is_active)
            VALUES (?, ?, ?, ?, 1)
        ''', (user_id, username, first_name, chat_id))
        
        conn.commit()
        conn.close()
    
    def _set_user_participation(self, user_id: int, opted_in: bool):
        """Set user's participation status for current week."""
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO weekly_participation (user_id, week_year, opted_in)
            VALUES (?, ?, ?)
        ''', (user_id, week, 1 if opted_in else 0))
        
        conn.commit()
        conn.close()
    
    def _get_participants(self) -> List[Dict]:
        """Get all users who opted in for this week, including busy status."""
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.user_id, u.username, u.first_name, u.chat_id, COALESCE(wp.is_busy, 0)
            FROM users u
            JOIN weekly_participation wp ON u.user_id = wp.user_id
            WHERE wp.week_year = ? AND wp.opted_in = 1 AND u.is_active = 1
        ''', (week,))
        
        participants = []
        for row in cursor.fetchall():
            participants.append({
                'user_id': row[0],
                'username': row[1],
                'first_name': row[2],
                'chat_id': row[3],
                'is_busy': bool(row[4])
            })
        
        conn.close()
        return participants

    def _get_participants_grouped(self) -> Dict[str, List[Dict]]:
        """Return participants grouped into unoccupied and occupied lists."""
        participants = self._get_participants()
        grouped = {
            'unoccupied': [],
            'occupied': []
        }

        for participant in participants:
            key = 'occupied' if participant['is_busy'] else 'unoccupied'
            grouped[key].append(participant)

        return grouped

    def _get_user_busy_status(self, user_id: int) -> Optional[bool]:
        """Return whether the user is marked busy for the week."""
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT opted_in, is_busy FROM weekly_participation
            WHERE user_id = ? AND week_year = ?
            ''',
            (user_id, week)
        )
        row = cursor.fetchone()
        conn.close()
        if not row or row[0] != 1:
            return None
        return bool(row[1])

    def _set_user_busy_status(self, user_id: int, busy: bool) -> bool:
        """Update busy status for an opted-in user. Returns True if updated."""
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT id FROM weekly_participation
            WHERE user_id = ? AND week_year = ? AND opted_in = 1
            ''',
            (user_id, week)
        )
        exists = cursor.fetchone()
        if not exists:
            conn.close()
            return False

        cursor.execute(
            '''
            UPDATE weekly_participation
            SET is_busy = ?
            WHERE user_id = ? AND week_year = ?
            ''',
            (1 if busy else 0, user_id, week)
        )
        conn.commit()
        conn.close()
        return True

    def _format_participant_lists_message(self) -> str:
        """Build a message showing unoccupied and occupied participants."""
        grouped = self._get_participants_grouped()
        week = self._get_current_week()
        header = f"🎉 People available to hang out this week ({week}):\n\n"

        def format_section(title: str, entries: List[Dict]) -> str:
            if not entries:
                return f"{title}:\n- None yet\n\n"
            lines = []
            for idx, participant in enumerate(entries, 1):
                username = f"@{participant['username']}" if participant['username'] else participant['first_name']
                lines.append(f"{idx}. {username}")
            return f"{title}:\n" + "\n".join(lines) + "\n\n"

        message = header
        message += format_section("🟢 Unoccupied", grouped['unoccupied'])
        message += format_section("🔴 Occupied", grouped['occupied'])

        total = len(grouped['unoccupied']) + len(grouped['occupied'])
        if total:
            message += f"👥 Total opted in: {total}\n\n"

        if not grouped['unoccupied'] and not grouped['occupied']:
            message += "No one has opted in yet. Use /optin to join the fun!\n\n"

        message += "Use the buttons below to update your status or refresh the lists."
        return message

    def _build_participant_list_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Return the inline keyboard for list interactions."""
        busy_status = self._get_user_busy_status(user_id)
        buttons: List[List[InlineKeyboardButton]] = []

        if busy_status is True:
            buttons.append([
                InlineKeyboardButton("Mark me unoccupied", callback_data="list_set_available")
            ])
        elif busy_status is False:
            buttons.append([
                InlineKeyboardButton("Mark me busy", callback_data="list_set_busy")
            ])

        buttons.append([
            InlineKeyboardButton("Refresh 🔄", callback_data="list_refresh")
        ])

        if busy_status is None:
            # Only refresh is meaningful if the user is not opted in yet
            return InlineKeyboardMarkup(buttons[-1:])

        return InlineKeyboardMarkup(buttons)
    
    def _get_all_active_users(self) -> List[Dict]:
        """Get all active users for sending reminders."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, username, first_name, chat_id
            FROM users
            WHERE is_active = 1
        ''')
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'user_id': row[0],
                'username': row[1],
                'first_name': row[2],
                'chat_id': row[3]
            })
        
        conn.close()
        return users

    def _is_admin(self, user_id: int) -> bool:
        """Check whether a user is an admin."""
        return user_id in self.admin_ids

    async def _ensure_admin(self, update: Update) -> bool:
        """Verify admin access for a command."""
        user = update.effective_user
        if user and self._is_admin(user.id):
            return True

        logger.warning("Unauthorized admin command attempt by user_id=%s", user.id if user else "unknown")
        if update.message:
            await update.message.reply_text("⛔ This command is restricted to admins.")
        return False

    def _reset_current_week_participation(self) -> int:
        """Delete participation records for the current week."""
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM weekly_participation WHERE week_year = ?',
            (week,)
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted

    def _get_weekly_status(self) -> Dict[str, int]:
        """Return counts for the current week."""
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        active_users = cursor.fetchone()[0] or 0

        cursor.execute(
            '''
            SELECT opted_in, COUNT(*)
            FROM weekly_participation
            WHERE week_year = ?
            GROUP BY opted_in
            ''',
            (week,)
        )

        opted_in = 0
        opted_out = 0
        responded = 0
        for row in cursor.fetchall():
            opted_flag, count = row
            responded += count
            if opted_flag == 1:
                opted_in = count
            else:
                opted_out += count

        conn.close()

        pending = max(active_users - responded, 0)
        return {
            'week': week,
            'active_users': active_users,
            'opted_in': opted_in,
            'opted_out': opted_out,
            'pending': pending
        }

    def _get_bot(self, context: Optional[ContextTypes.DEFAULT_TYPE]):
        """Resolve the bot instance from the context or application."""
        if context and getattr(context, 'bot', None):
            return context.bot
        if self.application:
            return self.application.bot
        raise RuntimeError("Bot application is not initialized yet.")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Add user to database
        self._add_user(user.id, user.username, user.first_name, chat_id)
        
        welcome_message = (
            f"👋 Hello {user.first_name}!\n\n"
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
        )
        
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_message = (
            "🤖 Social Chat Bot Commands:\n\n"
            "/start - Start the bot and register\n"
            "/optin - Opt in for this week's social matching\n"
            "/optout - Opt out for this week\n"
            "/status - Check your current participation status\n"
            "/list - See who's available to hang out this week\n"
            "/help - Show this help message\n\n"
            "You'll receive weekly reminders to participate!"
        )
        
        await update.message.reply_text(help_message)
    
    async def optin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /optin command."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Ensure user is in database
        self._add_user(user.id, user.username, user.first_name, chat_id)
        
        # Set participation
        self._set_user_participation(user.id, True)
        
        message = (
            "✅ Great! You're in for this week!\n\n"
            "I'll send you a list of other participants when the week starts.\n"
            "Use /list to see who's already signed up."
        )
        
        await update.message.reply_text(message)
    
    async def optout_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /optout command."""
        user = update.effective_user
        
        # Set participation to false
        self._set_user_participation(user.id, False)
        
        message = (
            "👋 No problem! You've opted out for this week.\n\n"
            "You can use /optin anytime to join again!"
        )
        
        await update.message.reply_text(message)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        user = update.effective_user
        week = self._get_current_week()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT opted_in FROM weekly_participation
            WHERE user_id = ? AND week_year = ?
        ''', (user.id, week))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] == 1:
            status = "✅ You're IN for this week's social matching!"
        else:
            status = "❌ You're currently opted out for this week."
        
        message = (
            f"📊 Your Status (Week {week}):\n\n"
            f"{status}\n\n"
            "Use /optin or /optout to change your status."
        )
        
        await update.message.reply_text(message)
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command - show all participants for this week."""
        user_id = update.effective_user.id
        message = self._format_participant_lists_message()
        reply_markup = self._build_participant_list_keyboard(user_id)

        await update.message.reply_text(message, reply_markup=reply_markup)

    async def list_callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button interactions for the participant list."""
        query = update.callback_query
        action = query.data
        user_id = query.from_user.id

        response = ""
        if action == "list_set_busy":
            updated = self._set_user_busy_status(user_id, True)
            if not updated:
                await query.answer("Please /optin before marking yourself busy.", show_alert=True)
                return
            response = "Marked you as busy."
        elif action == "list_set_available":
            updated = self._set_user_busy_status(user_id, False)
            if not updated:
                await query.answer("Please /optin before updating your status.", show_alert=True)
                return
            response = "Marked you as unoccupied."
        elif action == "list_refresh":
            response = "Lists refreshed."
        else:
            response = "Unknown action."

        message = self._format_participant_lists_message()
        reply_markup = self._build_participant_list_keyboard(user_id)

        try:
            await query.edit_message_text(message, reply_markup=reply_markup)
        except Exception as exc:
            logger.warning("Failed to edit message for list callback: %s", exc)

        await query.answer(response or "Done.")
    
    async def send_weekly_reminder(self, context: Optional[ContextTypes.DEFAULT_TYPE] = None):
        """Send weekly reminder to all active users."""
        users = self._get_all_active_users()
        week = self._get_current_week()
        bot = self._get_bot(context)
        
        logger.info(f"Sending weekly reminder to {len(users)} users for week {week}")
        
        message = (
            f"🔔 Weekly Social Reminder!\n\n"
            f"It's a new week ({week})! 🎉\n\n"
            "Would you like to be social this week?\n\n"
            "If yes, use /optin to join!\n"
            "You'll get a list of others who want to hang out too.\n\n"
            "Commands:\n"
            "/optin - I want to be social! ✅\n"
            "/optout - Not this week ❌\n"
            "/list - See who's already signed up"
        )
        
        sent_count = 0
        for user in users:
            try:
                await bot.send_message(
                    chat_id=user['chat_id'],
                    text=message
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send reminder to user {user['user_id']}: {e}")
        
        return sent_count
    
    async def send_participant_list(self, context: Optional[ContextTypes.DEFAULT_TYPE] = None):
        """Send list of participants to all who opted in."""
        participants = self._get_participants()
        week = self._get_current_week()
        bot = self._get_bot(context)
        
        if not participants:
            logger.info(f"No participants for week {week}, skipping list distribution")
            return
        
        logger.info(f"Sending participant list to {len(participants)} users for week {week}")
        list_message = self._format_participant_lists_message()
        
        # Send to all participants
        sent_count = 0
        for participant in participants:
            try:
                await bot.send_message(
                    chat_id=participant['chat_id'],
                    text=list_message,
                    reply_markup=self._build_participant_list_keyboard(participant['user_id'])
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send list to user {participant['user_id']}: {e}")
        
        return sent_count

    async def admin_start_optin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Allow admins to manually trigger the opt-in reminder."""
        if not await self._ensure_admin(update):
            return
        
        sent = await self.send_weekly_reminder(context)
        if sent:
            await update.message.reply_text(f"✅ Weekly reminder sent to {sent} active users.")
        else:
            await update.message.reply_text("⚠️ No active users found to notify.")

    async def admin_start_matching_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Allow admins to manually trigger participant matching."""
        if not await self._ensure_admin(update):
            return
        
        sent = await self.send_participant_list(context)
        if sent:
            await update.message.reply_text(f"📬 Participant list sent to {sent} opted-in users.")
        else:
            await update.message.reply_text("ℹ️ There are no participants to send a list to this week.")

    async def admin_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show weekly stats to admins."""
        if not await self._ensure_admin(update):
            return
        
        status = self._get_weekly_status()
        message = (
            f"📊 Weekly Status ({status['week']}):\n"
            f"• Active users: {status['active_users']}\n"
            f"• Opted in: {status['opted_in']}\n"
            f"• Opted out: {status['opted_out']}\n"
            f"• No response yet: {status['pending']}"
        )
        
        await update.message.reply_text(message)

    async def admin_reset_week_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reset participation data for the current week."""
        if not await self._ensure_admin(update):
            return
        
        deleted = self._reset_current_week_participation()
        week = self._get_current_week()
        await update.message.reply_text(
            f"🔄 Cleared {deleted} participation record(s) for week {week}."
        )
    
    def run(self):
        """Run the bot."""
        # Create application
        self.application = Application.builder().token(self.bot_token).build()
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("optin", self.optin_command))
        self.application.add_handler(CommandHandler("optout", self.optout_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("list", self.list_command))
        self.application.add_handler(CommandHandler("admin_optin", self.admin_start_optin_command))
        self.application.add_handler(CommandHandler("admin_matching", self.admin_start_matching_command))
        self.application.add_handler(CommandHandler("admin_status", self.admin_status_command))
        self.application.add_handler(CommandHandler("admin_reset", self.admin_reset_week_command))
        self.application.add_handler(CallbackQueryHandler(self.list_callback_handler, pattern="^list_"))
        
        # Schedule weekly reminder and matching
        reminder_day = self.config.get('reminder_day', 0)  # Monday by default
        reminder_time_str = self.config.get('reminder_time', '09:00')
        matching_day = self.config.get('matching_day', 0)  # Monday by default
        matching_time_str = self.config.get('matching_time', '12:00')
        
        # Parse times
        reminder_hour, reminder_minute = map(int, reminder_time_str.split(':'))
        matching_hour, matching_minute = map(int, matching_time_str.split(':'))
        
        # Add jobs to scheduler
        self.scheduler.add_job(
            self.send_weekly_reminder,
            CronTrigger(day_of_week=reminder_day, hour=reminder_hour, minute=reminder_minute),
            id='weekly_reminder'
        )
        
        self.scheduler.add_job(
            self.send_participant_list,
            CronTrigger(day_of_week=matching_day, hour=matching_hour, minute=matching_minute),
            id='send_matches'
        )
        
        # Start scheduler
        self.scheduler.start()
        logger.info("Scheduler started")
        
        # Start bot
        logger.info("Starting bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def load_config():
    """Load configuration from file or environment."""
    config = {}
    
    # Try to load from config.json
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
    
    # Override with environment variables if present
    bot_token = os.getenv('BOT_TOKEN') or config.get('bot_token')
    admin_env = os.getenv('ADMIN_IDS')
    if admin_env:
        config['admin_ids'] = _parse_admin_ids(admin_env)
    else:
        config['admin_ids'] = _parse_admin_ids(config.get('admin_ids'))
    
    if not bot_token:
        raise ValueError(
            "Bot token not found! Please set BOT_TOKEN environment variable "
            "or create config.json with bot_token field."
        )
    
    return bot_token, config


def main():
    """Main entry point."""
    try:
        bot_token, config = load_config()
        bot = SocialChatBot(bot_token, config)
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
