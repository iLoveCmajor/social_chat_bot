#!/usr/bin/env python3
"""
Social Chat Bot - Weekly Social Matching Bot for Telegram
Helps people find partners to hang out by matching weekly participants.
"""

import os
import json
import logging
from datetime import datetime, time
from typing import Dict, Set, List
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


class SocialChatBot:
    """Main bot class for handling social matching functionality."""
    
    def __init__(self, bot_token: str, config: dict):
        self.bot_token = bot_token
        self.config = config
        self.db_path = Path(__file__).parent / "bot_data.db"
        self.scheduler = AsyncIOScheduler()
        self.application = None
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
                UNIQUE(user_id, week_year)
            )
        ''')
        
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
        """Get all users who opted in for this week."""
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.user_id, u.username, u.first_name, u.chat_id
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
                'chat_id': row[3]
            })
        
        conn.close()
        return participants
    
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
        participants = self._get_participants()
        week = self._get_current_week()
        
        if not participants:
            message = (
                f"📭 No one has signed up yet for week {week}.\n\n"
                "Be the first! Use /optin to join."
            )
        else:
            message = f"🎉 People available to hang out this week ({week}):\n\n"
            
            for i, participant in enumerate(participants, 1):
                username = f"@{participant['username']}" if participant['username'] else participant['first_name']
                message += f"{i}. {username}\n"
            
            message += f"\n👥 Total: {len(participants)} people\n"
            message += "\nReach out to them and plan something fun!"
        
        await update.message.reply_text(message)
    
    async def send_weekly_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        """Send weekly reminder to all active users."""
        users = self._get_all_active_users()
        week = self._get_current_week()
        
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
        
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user['chat_id'],
                    text=message
                )
            except Exception as e:
                logger.error(f"Failed to send reminder to user {user['user_id']}: {e}")
    
    async def send_participant_list(self, context: ContextTypes.DEFAULT_TYPE):
        """Send list of participants to all who opted in."""
        participants = self._get_participants()
        week = self._get_current_week()
        
        if not participants:
            logger.info(f"No participants for week {week}, skipping list distribution")
            return
        
        logger.info(f"Sending participant list to {len(participants)} users for week {week}")
        
        # Create participant list message
        list_message = f"🎊 Your Social Matches for Week {week}!\n\n"
        list_message += "Here's everyone who wants to hang out this week:\n\n"
        
        for i, participant in enumerate(participants, 1):
            username = f"@{participant['username']}" if participant['username'] else participant['first_name']
            list_message += f"{i}. {username}\n"
        
        list_message += f"\n👥 Total: {len(participants)} people\n\n"
        list_message += "Reach out and plan something fun! 🎉\n"
        list_message += "Have a great week! 😊"
        
        # Send to all participants
        for participant in participants:
            try:
                await context.bot.send_message(
                    chat_id=participant['chat_id'],
                    text=list_message
                )
            except Exception as e:
                logger.error(f"Failed to send list to user {participant['user_id']}: {e}")
    
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
            args=[self.application.job_queue],
            id='weekly_reminder'
        )
        
        self.scheduler.add_job(
            self.send_participant_list,
            CronTrigger(day_of_week=matching_day, hour=matching_hour, minute=matching_minute),
            args=[self.application.job_queue],
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
