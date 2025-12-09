#!/usr/bin/env python3
"""
Social Chat Bot - Weekly Social Matching Bot for Telegram
Helps people find partners to hang out by matching weekly participants.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, List, Optional, Tuple
import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    Defaults,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from messages import TEXT, BUTTONS, RESPONSES, ALERTS

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
        tz_name = config.get('timezone') or os.getenv('BOT_TIMEZONE') or "Asia/Tbilisi"
        try:
            self.timezone = ZoneInfo(tz_name)
            self.timezone_name = tz_name
        except Exception:
            logger.warning("Invalid timezone %s, falling back to Asia/Tbilisi", tz_name)
            self.timezone = ZoneInfo("Asia/Tbilisi")
            self.timezone_name = "Asia/Tbilisi"
        self.scheduler = AsyncIOScheduler(timezone=self.timezone)
        self.application = None
        self.admin_ids: Set[int] = set(config.get('admin_ids', []))
        self._init_database()
        self.scheduler_jobs: List[str] = []
    
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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                target_user_id INTEGER,
                week_year TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, target_user_id, week_year)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_dislikes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                target_user_id INTEGER,
                week_year TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, target_user_id, week_year)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_state (
                week_year TEXT PRIMARY KEY,
                is_matching_phase INTEGER DEFAULT 0,
                matching_started_at DATETIME,
                phase TEXT DEFAULT 'optin',
                phase_started_at DATETIME
            )
        ''')

        cursor.execute("PRAGMA table_info(weekly_state)")
        ws_columns = [row[1] for row in cursor.fetchall()]
        if 'phase' not in ws_columns:
            cursor.execute("ALTER TABLE weekly_state ADD COLUMN phase TEXT DEFAULT 'optin'")
        if 'phase_started_at' not in ws_columns:
            cursor.execute("ALTER TABLE weekly_state ADD COLUMN phase_started_at DATETIME")

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def _now(self) -> datetime:
        """Return current datetime in configured timezone."""
        return datetime.now(self.timezone)

    def _get_current_week(self) -> str:
        """Get current week identifier (year-week)."""
        now = self._now()
        return f"{now.year}-W{now.isocalendar()[1]:02d}"

    def _get_current_week_range(self):
        """Return date objects representing the Monday-Sunday range for this week."""
        today = self._now().date()
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start, end

    def _get_current_week_label(self) -> str:
        """Return formatted week range as ddmmyyyy - ddmmyyyy."""
        start, end = self._get_current_week_range()
        return f"{start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}"
    
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
            INSERT INTO weekly_participation (user_id, week_year, opted_in)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, week_year)
            DO UPDATE SET opted_in = excluded.opted_in
        ''', (user_id, week, 1 if opted_in else 0))

        if not opted_in:
            cursor.execute(
                '''
                DELETE FROM weekly_likes
                WHERE week_year = ? AND (user_id = ? OR target_user_id = ?)
                ''',
                (week, user_id, user_id)
            )
            cursor.execute(
                '''
                DELETE FROM weekly_dislikes
                WHERE week_year = ? AND (user_id = ? OR target_user_id = ?)
                ''',
                (week, user_id, user_id)
            )
        
        conn.commit()
        conn.close()

        if opted_in:
            self._initialize_likes_for_user(user_id)
    
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

    def _is_user_opted_in(self, user_id: int) -> bool:
        """Return True if the user is opted in for the current week."""
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT opted_in FROM weekly_participation
            WHERE user_id = ? AND week_year = ?
            ''',
            (user_id, week)
        )
        row = cursor.fetchone()
        conn.close()
        return bool(row and row[0] == 1)

    def _get_participation_state(self, user_id: int) -> Tuple[bool, bool]:
        """Return (has_responded, is_opted_in) for current week."""
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT opted_in FROM weekly_participation
            WHERE user_id = ? AND week_year = ?
            ''',
            (user_id, week)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return False, False
        return True, bool(row[0])

    def _get_user_likes(self, user_id: int) -> Set[int]:
        """Return a set of user IDs liked by the user this week."""
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT target_user_id FROM weekly_likes
            WHERE user_id = ? AND week_year = ?
            ''',
            (user_id, week)
        )
        liked = {row[0] for row in cursor.fetchall()}
        conn.close()
        return liked

    def _get_user_dislikes(self, user_id: int) -> Set[int]:
        """Return a set of user IDs explicitly disliked by the user this week."""
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT target_user_id FROM weekly_dislikes
            WHERE user_id = ? AND week_year = ?
            ''',
            (user_id, week)
        )
        disliked = {row[0] for row in cursor.fetchall()}
        conn.close()
        return disliked

    def _set_like_status(self, user_id: int, target_user_id: int, like: bool) -> bool:
        """Like or unlike another user. Returns True if applied."""
        if user_id == target_user_id:
            return False
        if self._get_week_phase() != 'liking':
            return False
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT 1 FROM weekly_participation
            WHERE user_id = ? AND week_year = ? AND opted_in = 1
            ''',
            (user_id, week)
        )
        user_opted_in = cursor.fetchone()

        cursor.execute(
            '''
            SELECT 1 FROM weekly_participation
            WHERE user_id = ? AND week_year = ? AND opted_in = 1
            ''',
            (target_user_id, week)
        )
        target_opted_in = cursor.fetchone()

        if not user_opted_in or not target_opted_in:
            conn.close()
            return False

        if like:
            cursor.execute(
                '''
                INSERT OR IGNORE INTO weekly_likes (user_id, target_user_id, week_year)
                VALUES (?, ?, ?)
                ''',
                (user_id, target_user_id, week)
            )
        else:
            cursor.execute(
                '''
                DELETE FROM weekly_likes
                WHERE user_id = ? AND target_user_id = ? AND week_year = ?
                ''',
                (user_id, target_user_id, week)
            )

        conn.commit()
        conn.close()
        return True

    def _initialize_likes_for_user(self, user_id: int):
        """Auto-like all other participants for a newly opted-in user (unless disliked)."""
        if self._is_matching_phase_active():
            return
        participants = self._get_participants()
        week = self._get_current_week()
        others = [p['user_id'] for p in participants if p['user_id'] != user_id]
        if not others:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT target_user_id FROM weekly_dislikes
            WHERE user_id = ? AND week_year = ?
            ''',
            (user_id, week)
        )
        disliked_targets = {row[0] for row in cursor.fetchall()}
        auto_like_targets = [target for target in others if target not in disliked_targets]
        if auto_like_targets:
            cursor.executemany(
                '''
                INSERT OR IGNORE INTO weekly_likes (user_id, target_user_id, week_year)
                VALUES (?, ?, ?)
                ''',
                [(user_id, target_id, week) for target_id in auto_like_targets]
            )

        cursor.execute(
            '''
            SELECT user_id FROM weekly_dislikes
            WHERE target_user_id = ? AND week_year = ?
            ''',
            (user_id, week)
        )
        disliked_by_users = {row[0] for row in cursor.fetchall()}
        reciprocal_sources = [source for source in others if source not in disliked_by_users]
        if reciprocal_sources:
            cursor.executemany(
                '''
                INSERT OR IGNORE INTO weekly_likes (user_id, target_user_id, week_year)
                VALUES (?, ?, ?)
                ''',
                [(source_id, user_id, week) for source_id in reciprocal_sources]
            )

        conn.commit()
        conn.close()

    def _set_dislike_status(self, user_id: int, target_user_id: int, dislike: bool) -> bool:
        """Mark/unmark a target as disliked. Returns True if applied."""
        if user_id == target_user_id:
            return False
        if self._get_week_phase() != 'liking':
            return False
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT 1 FROM weekly_participation
            WHERE user_id = ? AND week_year = ? AND opted_in = 1
            ''',
            (user_id, week)
        )
        user_opted_in = cursor.fetchone()

        cursor.execute(
            '''
            SELECT 1 FROM weekly_participation
            WHERE user_id = ? AND week_year = ? AND opted_in = 1
            ''',
            (target_user_id, week)
        )
        target_opted_in = cursor.fetchone()

        if not user_opted_in or not target_opted_in:
            conn.close()
            return False

        if dislike:
            cursor.execute(
                '''
                DELETE FROM weekly_likes
                WHERE user_id = ? AND target_user_id = ? AND week_year = ?
                ''',
                (user_id, target_user_id, week)
            )
            cursor.execute(
                '''
                INSERT OR IGNORE INTO weekly_dislikes (user_id, target_user_id, week_year)
                VALUES (?, ?, ?)
                ''',
                (user_id, target_user_id, week)
            )
        else:
            cursor.execute(
                '''
                DELETE FROM weekly_dislikes
                WHERE user_id = ? AND target_user_id = ? AND week_year = ?
                ''',
                (user_id, target_user_id, week)
            )
            cursor.execute(
                '''
                INSERT OR IGNORE INTO weekly_likes (user_id, target_user_id, week_year)
                VALUES (?, ?, ?)
                ''',
                (user_id, target_user_id, week)
            )

        conn.commit()
        conn.close()
        return True

    def _dislike_all_participants(self, user_id: int):
        """Mark every other participant as disliked."""
        if self._get_week_phase() != 'liking':
            return
        targets = [p['user_id'] for p in self._get_participants() if p['user_id'] != user_id]
        for target_id in targets:
            self._set_dislike_status(user_id, target_id, True)

    def _generate_weekly_pairings(self, participants: Dict[int, Dict]) -> Dict[int, Optional[int]]:
        """Return a mapping of user_id -> matched user_id (or None) for this week."""
        if not participants:
            return {}

        participant_ids = set(participants.keys())
        likes_graph: Dict[int, Set[int]] = {user_id: set() for user_id in participant_ids}

        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT user_id, target_user_id
            FROM weekly_likes
            WHERE week_year = ?
            ''',
            (week,)
        )

        for liker_id, target_id in cursor.fetchall():
            if liker_id in likes_graph and target_id in participant_ids:
                likes_graph[liker_id].add(target_id)

        conn.close()

        possible_pairs: List[Tuple[int, int]] = []
        for user_id, liked_users in likes_graph.items():
            for target_id in liked_users:
                if target_id not in likes_graph:
                    continue
                if user_id < target_id and user_id in likes_graph[target_id]:
                    possible_pairs.append((user_id, target_id))

        possible_pairs.sort(key=lambda pair: (pair[0], pair[1]))

        matches: Dict[int, Optional[int]] = {user_id: None for user_id in participant_ids}
        used: Set[int] = set()
        for user_a, user_b in possible_pairs:
            if user_a in used or user_b in used:
                continue
            matches[user_a] = user_b
            matches[user_b] = user_a
            used.add(user_a)
            used.add(user_b)

        return matches

    def _get_week_relationships(self) -> Tuple[Dict[int, Set[int]], Dict[int, Set[int]]]:
        """Return dictionaries of likes and dislikes for the current week."""
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        likes_map: Dict[int, Set[int]] = {}
        dislikes_map: Dict[int, Set[int]] = {}

        cursor.execute(
            '''
            SELECT user_id, target_user_id FROM weekly_likes
            WHERE week_year = ?
            ''',
            (week,)
        )
        for user_id, target_id in cursor.fetchall():
            likes_map.setdefault(user_id, set()).add(target_id)

        cursor.execute(
            '''
            SELECT user_id, target_user_id FROM weekly_dislikes
            WHERE week_year = ?
            ''',
            (week,)
        )
        for user_id, target_id in cursor.fetchall():
            dislikes_map.setdefault(user_id, set()).add(target_id)

        conn.close()
        return likes_map, dislikes_map

    def _get_display_name(self, participant: Dict) -> str:
        username = participant.get('username')
        if username:
            return f"@{username}"
        return participant.get('first_name') or TEXT["unknown_user"]

    def _build_status_message(self, user_id: int) -> str:
        week_label = self._get_current_week_label()
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT opted_in FROM weekly_participation
            WHERE user_id = ? AND week_year = ?
            ''',
            (user_id, week)
        )
        result = cursor.fetchone()
        conn.close()
        status_text = TEXT["status_in"] if result and result[0] == 1 else TEXT["status_out"]
        return TEXT["status_summary"].format(week_label=week_label, status=status_text)

    def _build_matching_phase_message(self, user_id: int) -> str:
        """Construct the matching view text for the user."""
        week_label = self._get_current_week_label()
        phase = self._get_week_phase()
        user_opted_in = self._is_user_opted_in(user_id)
        participants = self._get_participants()
        participant_lookup = {p['user_id']: p for p in participants}
        lines: List[str] = []

        if phase == 'matching':
            if not user_opted_in:
                return TEXT["matching_phase_change_locked_notoptedin"]
            pairings = self._generate_weekly_pairings(participant_lookup)
            partner_id = pairings.get(user_id)
            partner = participant_lookup.get(partner_id) if partner_id else None
            if partner:
                lines.append(TEXT["matching_pair_announcement"].format(
                    name=self._get_display_name(partner)
                ))
            else:
                lines.append(TEXT["matching_no_matches"])
            return "\n".join(lines)

        if phase == 'liking' and not user_opted_in:
            return TEXT["liking_phase_optin_closed"]

        if phase == 'optin':
            if not user_opted_in:
                lines.append(TEXT["matching_not_opted"])
            else:
                lines.append(TEXT["matching_opted_in_waiting"])
            return "\n".join(lines)

        # Liking phase for opted-in users
        likes = self._get_user_likes(user_id)
        dislikes = self._get_user_dislikes(user_id)
        others = [p for p in participants if p['user_id'] != user_id]
        if not others:
            return TEXT["matching_no_participants"]

        lines.append(TEXT["matching_participants_header"])
        lines.append("")
        for idx, participant in enumerate(others, 1):
            participant_id = participant['user_id']
            if participant_id in dislikes:
                state = TEXT["matching_disliked"]
            elif participant_id in likes:
                state = TEXT["matching_liked"]
            else:
                state = ""
            lines.append(
                TEXT["matching_participant_line"].format(
                    idx=idx,
                    name=self._get_display_name(participant),
                    state=state
                )
            )
        lines.append("")
        lines.append(TEXT["matching_instructions"])
        lines.append("")
        lines.append(TEXT["matching_waiting_notice"])
        return "\n".join(lines)

    def _build_optin_choice_keyboard(self) -> InlineKeyboardMarkup:
        """Return inline keyboard with opt-in/out choices."""
        return InlineKeyboardMarkup([[
            InlineKeyboardButton(BUTTONS["optin"], callback_data="list_optin"),
            InlineKeyboardButton(BUTTONS["optout"], callback_data="list_optout")
        ]])

    def _build_intro_keyboard(self, include_no: bool = True) -> InlineKeyboardMarkup:
        """Return intro buttons for onboarding choices."""
        buttons: List[List[InlineKeyboardButton]] = [
            [InlineKeyboardButton(BUTTONS["intro_yes"], callback_data="intro_yes")]
        ]
        if include_no:
            buttons[0].append(
                InlineKeyboardButton(BUTTONS["intro_no"], callback_data="intro_no")
            )
        return InlineKeyboardMarkup(buttons)

    def _build_matching_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Return inline buttons for liking/unliking and status controls."""
        phase = self._get_week_phase()

        if phase == 'optin':
            responded, _ = self._get_participation_state(user_id)
            if not responded:
                return self._build_optin_choice_keyboard()
            return InlineKeyboardMarkup([[
                InlineKeyboardButton(BUTTONS["change_mind"], callback_data="list_change_mind")
            ]])

        if not self._is_user_opted_in(user_id):
            return InlineKeyboardMarkup([])

        if phase == 'matching':
            return InlineKeyboardMarkup([])

        participants = [p for p in self._get_participants() if p['user_id'] != user_id]
        dislikes = self._get_user_dislikes(user_id)
        buttons: List[List[InlineKeyboardButton]] = []

        for participant in participants:
            name = self._get_display_name(participant)
            pid = participant['user_id']
            if pid in dislikes:
                buttons.append([
                    InlineKeyboardButton(
                        BUTTONS["like"].format(name=name),
                        callback_data=f"list_like_{pid}"
                    )
                ])
            else:
                buttons.append([
                    InlineKeyboardButton(
                        BUTTONS["unlike"].format(name=name),
                        callback_data=f"list_unlike_{pid}"
                    )
                ])

        if phase == 'liking':
            if not participants:
                return InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        BUTTONS["no_participants_ack"],
                        callback_data="list_no_participants_ack"
                    )
                ]])
            buttons.append([
                InlineKeyboardButton(BUTTONS["optout_final"], callback_data="list_dislike_all")
            ])

        return InlineKeyboardMarkup(buttons)

    def _build_main_menu_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Return inline buttons for global user actions."""
        phase = self._get_week_phase()
        opted_in = self._is_user_opted_in(user_id)
        buttons: List[List[InlineKeyboardButton]] = []

        if phase == 'optin':
            responded, _ = self._get_participation_state(user_id)
            if not responded:
                return self._build_optin_choice_keyboard()
            buttons.append([
                InlineKeyboardButton(BUTTONS["change_mind"], callback_data="list_change_mind")
            ])
        elif phase == 'liking' and opted_in:
            other_participants = [p for p in self._get_participants() if p['user_id'] != user_id]
            if not other_participants:
                buttons.append([
                    InlineKeyboardButton(
                        BUTTONS["no_participants_ack"],
                        callback_data="list_no_participants_ack"
                    )
                ])
            else:
                buttons.append([
                    InlineKeyboardButton(BUTTONS["optout_final"], callback_data="list_dislike_all")
                ])
        return InlineKeyboardMarkup(buttons)

    def _normalize_days(self, value, fallback: int) -> List[int]:
        """Return a list of weekday integers from config values."""
        if value is None:
            return [fallback]
        if isinstance(value, (list, tuple, set)):
            days = []
            for item in value:
                try:
                    days.append(int(item))
                except (TypeError, ValueError):
                    logger.warning("Ignoring invalid day value: %s", item)
            return days or [fallback]
        try:
            return [int(value)]
        except (TypeError, ValueError):
            logger.warning("Invalid day value %s, using fallback %s", value, fallback)
            return [fallback]
    
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
            await update.message.reply_text(TEXT["admin_only"])
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
        cursor.execute(
            'DELETE FROM weekly_likes WHERE week_year = ?',
            (week,)
        )
        cursor.execute(
            'DELETE FROM weekly_dislikes WHERE week_year = ?',
            (week,)
        )
        cursor.execute(
            'DELETE FROM weekly_state WHERE week_year = ?',
            (week,)
        )
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
            'week_range': self._get_current_week_label(),
            'active_users': active_users,
            'opted_in': opted_in,
            'opted_out': opted_out,
            'pending': pending
        }

    def _get_week_phase(self) -> str:
        """Return current phase identifier: optin, liking, or matching."""
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT phase, is_matching_phase
            FROM weekly_state
            WHERE week_year = ?
            ''',
            (week,)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return 'optin'
        phase, is_matching = row
        if phase:
            return phase
        return 'matching' if (is_matching == 1) else 'optin'

    def _set_week_phase(self, phase: str):
        """Persist the current weekly phase."""
        valid_phases = {'optin', 'liking', 'matching'}
        if phase not in valid_phases:
            raise ValueError(f"Invalid phase: {phase}")

        week = self._get_current_week()
        is_matching = 1 if phase == 'matching' else 0
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO weekly_state (week_year, is_matching_phase, matching_started_at, phase, phase_started_at)
            VALUES (?, ?, CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE NULL END, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(week_year)
            DO UPDATE SET
                is_matching_phase = excluded.is_matching_phase,
                matching_started_at = CASE
                    WHEN excluded.is_matching_phase = 1 THEN CURRENT_TIMESTAMP
                    ELSE matching_started_at
                END,
                phase = excluded.phase,
                phase_started_at = CURRENT_TIMESTAMP
            ''',
            (week, is_matching, is_matching, phase)
        )
        conn.commit()
        conn.close()

    def _is_matching_phase_active(self) -> bool:
        """Return True if the current week is in the matching phase."""
        return self._get_week_phase() == 'matching'

    def _start_matching_phase(self):
        """Mark the current week as being in the matching phase."""
        self._set_week_phase('matching')

    def _reset_matching_phase(self):
        """Clear any stored matching phase marker for the current week."""
        week = self._get_current_week()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM weekly_state WHERE week_year = ?', (week,))
        conn.commit()
        conn.close()

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
        
        welcome_message = TEXT["welcome"].format(first_name=user.first_name)
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=self._build_intro_keyboard()
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_message = TEXT["help"]
        
        await update.message.reply_text(
            help_message,
            reply_markup=self._build_main_menu_keyboard(update.effective_user.id)
        )
    
    async def optin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /optin command."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        phase = self._get_week_phase()

        if phase == 'matching':
            if self._is_user_opted_in(user.id):
                await update.message.reply_text(TEXT["matching_phase_change_locked_optedin"])
                matching_message = self._build_matching_phase_message(user.id)
                reply_markup = self._build_matching_keyboard(user.id)
                await update.message.reply_text(matching_message, reply_markup=reply_markup)
            else:
                await update.message.reply_text(TEXT["matching_phase_change_locked_notoptedin"])
            return
        if phase == 'liking':
            if self._is_user_opted_in(user.id):
                await update.message.reply_text(TEXT["liking_phase_already_in"])
                matching_message = self._build_matching_phase_message(user.id)
                reply_markup = self._build_matching_keyboard(user.id)
                await update.message.reply_text(matching_message, reply_markup=reply_markup)
            else:
                await update.message.reply_text(TEXT["liking_phase_optin_closed"])
            return
        
        # Ensure user is in database
        self._add_user(user.id, user.username, user.first_name, chat_id)
        
        # Set participation
        self._set_user_participation(user.id, True)
        
        message = TEXT["optin_confirmation"]
        
        await update.message.reply_text(message)

        matching_message = self._build_matching_phase_message(user.id)
        reply_markup = self._build_matching_keyboard(user.id)
        await update.message.reply_text(matching_message, reply_markup=reply_markup)
    
    async def optout_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /optout command."""
        user = update.effective_user
        if self._is_matching_phase_active():
            if self._is_user_opted_in(user.id):
                await update.message.reply_text(TEXT["matching_phase_change_locked_optedin"])
                matching_message = self._build_matching_phase_message(user.id)
                reply_markup = self._build_matching_keyboard(user.id)
                await update.message.reply_text(matching_message, reply_markup=reply_markup)
            else:
                await update.message.reply_text(TEXT["matching_phase_change_locked_notoptedin"])
            return
        
        # Set participation to false
        self._set_user_participation(user.id, False)
        
        message = TEXT["optout_confirmation"]
        
        await update.message.reply_text(message)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        user = update.effective_user
        message = self._build_status_message(user.id)
        
        await update.message.reply_text(
            message,
            reply_markup=self._build_main_menu_keyboard(user.id)
        )
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command - show all participants for this week."""
        user_id = update.effective_user.id
        message = self._build_matching_phase_message(user_id)
        reply_markup = self._build_matching_keyboard(user_id)

        await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def intro_callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle onboarding buttons shown after /start."""
        query = update.callback_query
        action = query.data
        user_id = query.from_user.id

        if action == "intro_yes":
            await query.answer()
            user = query.from_user
            first_name = user.first_name or "Friend"
            phase = self._get_week_phase()
            responded, _ = self._get_participation_state(user_id)

            if phase == 'optin':
                await query.message.reply_text(TEXT["welcome_yes_response"])
                weekly_message = TEXT["weekly_reminder"].format(first_name=first_name)
                followup_markup = (
                    self._build_optin_choice_keyboard()
                    if not responded
                    else self._build_main_menu_keyboard(user_id)
                )
                await query.message.reply_text(
                    weekly_message,
                    reply_markup=followup_markup
                )
            else:
                await query.message.reply_text(
                    TEXT["welcome_yes_response"],
                    reply_markup=self._build_main_menu_keyboard(user_id)
                )
            return

        if action == "intro_no":
            await query.answer()
            await query.message.reply_text(
                TEXT["welcome_no_response"],
                reply_markup=self._build_intro_keyboard(include_no=False)
            )
            return

        await query.answer()

    async def list_callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button interactions for the participant list."""
        query = update.callback_query
        action = query.data
        user_id = query.from_user.id
        matching_locked = self._is_matching_phase_active()
        liking_active = self._get_week_phase() == 'liking'

        response = ""
        if action == "list_optin":
            if self._get_week_phase() != 'optin':
                await query.answer(ALERTS["optin_phase_only"], show_alert=True)
                return
            self._set_user_participation(user_id, True)
            response = RESPONSES["optin_set"]
        elif action == "list_optout":
            if self._get_week_phase() != 'optin':
                await query.answer(ALERTS["optin_phase_only"], show_alert=True)
                return
            self._set_user_participation(user_id, False)
            response = RESPONSES["optout_set"]
        elif action == "list_dislike_all":
            if self._get_week_phase() != 'liking':
                await query.answer(ALERTS["liking_locked"], show_alert=True)
                return
            self._dislike_all_participants(user_id)
            response = RESPONSES["dislike_all_set"]
        elif action == "list_change_mind":
            if self._get_week_phase() != 'optin':
                await query.answer(ALERTS["optin_phase_only"], show_alert=True)
                return
            await query.answer()
            try:
                await query.edit_message_text(
                    TEXT["change_mind_prompt"],
                    reply_markup=self._build_optin_choice_keyboard()
                )
            except Exception as exc:
                logger.warning("Failed to edit message for change mind: %s", exc)
            return
        elif action == "list_no_participants_ack":
            if self._get_week_phase() != 'liking':
                await query.answer(ALERTS["liking_locked"], show_alert=True)
                return
            await query.answer()
            await query.message.reply_text(TEXT["matching_no_participants_followup"])
            return
        elif action.startswith("list_like_"):
            if matching_locked:
                await query.answer(ALERTS["matching_locked"], show_alert=True)
                return
            if not liking_active:
                await query.answer(ALERTS["liking_locked"], show_alert=True)
                return
            target_id = int(action.split('_')[-1])
            if not self._set_dislike_status(user_id, target_id, False):
                await query.answer(ALERTS["like_requires_optin"], show_alert=True)
                return
            response = RESPONSES["dislike_removed"]
        elif action.startswith("list_unlike_"):
            if matching_locked:
                await query.answer(ALERTS["matching_locked"], show_alert=True)
                return
            if not liking_active:
                await query.answer(ALERTS["liking_locked"], show_alert=True)
                return
            target_id = int(action.split('_')[-1])
            if not self._set_dislike_status(user_id, target_id, True):
                await query.answer(ALERTS["dislike_failed"], show_alert=True)
                return
            response = RESPONSES["dislike_success"]
        elif action == "list_status":
            status_text = self._build_status_message(user_id)
            await query.message.reply_text(
                status_text,
                reply_markup=self._build_main_menu_keyboard(user_id)
            )
            response = RESPONSES["done"]
        elif action == "list_help":
            await query.message.reply_text(
                TEXT["help"],
                reply_markup=self._build_main_menu_keyboard(user_id)
            )
            response = RESPONSES["done"]
        elif action == "list_refresh":
            response = RESPONSES["refresh"]
        else:
            response = RESPONSES["unknown"]

        message = self._build_matching_phase_message(user_id)
        reply_markup = self._build_matching_keyboard(user_id)

        try:
            await query.edit_message_text(message, reply_markup=reply_markup)
        except Exception as exc:
            logger.warning("Failed to edit message for list callback: %s", exc)

        await query.answer(response or RESPONSES["done"])
    
    async def send_weekly_reminder(self, context: Optional[ContextTypes.DEFAULT_TYPE] = None):
        """Send weekly reminder to all active users."""
        self._set_week_phase('optin')
        users = self._get_all_active_users()
        week = self._get_current_week()
        bot = self._get_bot(context)
        
        logger.info(f"Sending weekly reminder to {len(users)} users for week {week}")
        
        sent_count = 0
        for user in users:
            first_name = user.get('first_name') or "User"
            message = TEXT["weekly_reminder"].format(first_name=first_name)
            try:
                await bot.send_message(
                    chat_id=user['chat_id'],
                    text=message,
                    reply_markup=self._build_main_menu_keyboard(user['user_id'])
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send reminder to user {user['user_id']}: {e}")
        
        return sent_count
    
    async def _broadcast_phase_dashboards(self, context: Optional[ContextTypes.DEFAULT_TYPE] = None):
        """Send the current phase dashboard to opted-in users."""
        participants = self._get_participants()
        week = self._get_current_week()
        bot = self._get_bot(context)

        if not participants:
            logger.info(f"No participants for week {week}, skipping list distribution")
            return
        
        logger.info(f"Sending phase dashboard ({self._get_week_phase()}) to {len(participants)} users for week {week}")
        
        # Send to all participants
        sent_count = 0
        for participant in participants:
            try:
                await bot.send_message(
                    chat_id=participant['chat_id'],
                    text=self._build_matching_phase_message(participant['user_id']),
                    reply_markup=self._build_matching_keyboard(participant['user_id'])
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send list to user {participant['user_id']}: {e}")
        
        return sent_count

    async def send_participant_list(self, context: Optional[ContextTypes.DEFAULT_TYPE] = None):
        """Send final matches (matching phase) to all participants."""
        participants = self._get_participants()
        if len(participants) <= 1:
            logger.info("Not enough participants to start matching phase; staying in liking phase.")
            return 0
        self._start_matching_phase()
        return await self._broadcast_phase_dashboards(context)

    async def send_liking_phase_list(self, context: Optional[ContextTypes.DEFAULT_TYPE] = None):
        """Send liking phase dashboards to opted-in users."""
        self._set_week_phase('liking')
        return await self._broadcast_phase_dashboards(context)

    async def admin_next_phase_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Advance the weekly process to the next phase."""
        if not await self._ensure_admin(update):
            return

        phase = self._get_week_phase()
        participants = self._get_participants()

        if not participants:
            await update.message.reply_text(TEXT["admin_next_phase_none"])
            return

        if phase == 'matching':
            await update.message.reply_text(TEXT["admin_next_phase_blocked"])
            return

        if phase == 'liking' and len(participants) <= 1:
            self._set_week_phase('optin')
            await update.message.reply_text(TEXT["admin_next_phase_insufficient"])
            return

        if phase == 'optin':
            sent = await self.send_liking_phase_list(context)
            if sent:
                await update.message.reply_text(TEXT["admin_next_phase_liking_sent"].format(count=sent))
            else:
                await update.message.reply_text(TEXT["admin_next_phase_none"])
            return

        # phase == 'liking'
        sent = await self.send_participant_list(context)
        if sent:
            await update.message.reply_text(TEXT["admin_next_phase_matching_sent"].format(count=sent))
        else:
            await update.message.reply_text(TEXT["admin_next_phase_none"])

    async def admin_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin overview of participants/matches depending on phase."""
        if not await self._ensure_admin(update):
            return

        participants = self._get_participants()
        participant_lookup = {p['user_id']: p for p in participants}
        week_label = self._get_current_week_label()

        if not participants:
            await update.message.reply_text(
                TEXT["admin_list_no_participants"].format(week_label=week_label)
            )
            return

        likes_map, dislikes_map = self._get_week_relationships()

        if not self._is_matching_phase_active():
            lines = [TEXT["admin_list_optin_header"].format(week_label=week_label)]
            sorted_participants = sorted(
                participants,
                key=lambda p: self._get_display_name(p).lower()
            )
            for participant in sorted_participants:
                user_id = participant['user_id']
                like_names = [
                    self._get_display_name(participant_lookup.get(target_id, {}))
                    for target_id in sorted(likes_map.get(user_id, set()))
                    if target_id in participant_lookup
                ]
                dislike_names = [
                    self._get_display_name(participant_lookup.get(target_id, {}))
                    for target_id in sorted(dislikes_map.get(user_id, set()))
                    if target_id in participant_lookup
                ]
                likes_text = ", ".join(like_names) if like_names else TEXT["admin_list_none"]
                dislikes_text = ", ".join(dislike_names) if dislike_names else TEXT["admin_list_none"]
                lines.append(
                    TEXT["admin_list_participant_line"].format(
                        name=self._get_display_name(participant),
                        likes=likes_text,
                        dislikes=dislikes_text
                    )
                )
            await update.message.reply_text("\n".join(lines))
            return

        pairings = self._generate_weekly_pairings(participant_lookup)
        seen: Set[int] = set()
        pairs: List[Tuple[int, int]] = []
        unmatched: List[int] = []

        for user_id, partner_id in pairings.items():
            if partner_id:
                pair_key = tuple(sorted((user_id, partner_id)))
                if pair_key[0] in seen or pair_key[1] in seen:
                    continue
                pairs.append(pair_key)
                seen.update(pair_key)
            else:
                unmatched.append(user_id)

        pairs.sort(key=lambda ids: (self._get_display_name(participant_lookup[ids[0]]).lower(),
                                    self._get_display_name(participant_lookup[ids[1]]).lower()))
        unmatched = sorted(
            {uid for uid in unmatched if uid in participant_lookup},
            key=lambda uid: self._get_display_name(participant_lookup[uid]).lower()
        )

        lines = [TEXT["admin_pairs_header"].format(week_label=week_label)]
        if pairs:
            for idx, (user_a, user_b) in enumerate(pairs, 1):
                name_a = self._get_display_name(participant_lookup[user_a])
                name_b = self._get_display_name(participant_lookup[user_b])
                lines.append(TEXT["admin_pairs_line"].format(idx=idx, name_a=name_a, name_b=name_b))
        else:
            lines.append(TEXT["admin_pairs_none"])

        lines.append("")
        lines.append(TEXT["admin_list_unmatched_header"])
        if unmatched:
            for user_id in unmatched:
                lines.append(TEXT["admin_list_unmatched_line"].format(
                    name=self._get_display_name(participant_lookup[user_id])
                ))
        else:
            lines.append(TEXT["admin_list_unmatched_none"])

        await update.message.reply_text("\n".join(lines))

    async def admin_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show weekly stats to admins."""
        if not await self._ensure_admin(update):
            return
        
        status = self._get_weekly_status()
        message = TEXT["admin_status"].format(
            week_label=status['week_range'],
            active=status['active_users'],
            opted_in=status['opted_in'],
            opted_out=status['opted_out'],
            pending=status['pending']
        )
        
        await update.message.reply_text(message)

    async def admin_reset_week_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reset participation data for the current week."""
        if not await self._ensure_admin(update):
            return
        
        deleted = self._reset_current_week_participation()
        week_label = self._get_current_week_label()
        notified = await self.send_weekly_reminder(context) or 0
        await update.message.reply_text(
            TEXT["admin_reset"].format(count=deleted, week_label=week_label, notified=notified)
        )
    
    def run(self):
        """Run the bot."""
        # Create application with HTML parsing enabled for outgoing messages
        defaults = Defaults(parse_mode=ParseMode.HTML)
        self.application = (
            Application.builder()
            .token(self.bot_token)
            .defaults(defaults)
            .build()
        )
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("optin", self.optin_command))
        self.application.add_handler(CommandHandler("optout", self.optout_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("list", self.list_command))
        self.application.add_handler(CommandHandler("admin_next_phase", self.admin_next_phase_command))
        self.application.add_handler(CommandHandler("admin_list", self.admin_list_command))
        self.application.add_handler(CommandHandler("admin_status", self.admin_status_command))
        self.application.add_handler(CommandHandler("admin_reset", self.admin_reset_week_command))
        self.application.add_handler(CallbackQueryHandler(self.intro_callback_handler, pattern="^intro_"))
        self.application.add_handler(CallbackQueryHandler(self.list_callback_handler, pattern="^list_"))
        
        # Schedule weekly reminder and matching
        reminder_days_config = self.config.get('reminder_days', self.config.get('reminder_day'))
        reminder_days = self._normalize_days(reminder_days_config, 0)
        reminder_time_str = self.config.get('reminder_time', '09:00')

        liking_days_config = self.config.get('liking_days', self.config.get('liking_day', reminder_days[0]))
        liking_days = self._normalize_days(liking_days_config, reminder_days[0])
        liking_time_str = self.config.get('liking_time', '11:00')

        matching_days_config = self.config.get('matching_days', self.config.get('matching_day', 0))
        matching_days = self._normalize_days(matching_days_config, 0)
        matching_time_str = self.config.get('matching_time', '12:00')
        
        # Parse times
        reminder_hour, reminder_minute = map(int, reminder_time_str.split(':'))
        liking_hour, liking_minute = map(int, liking_time_str.split(':'))
        matching_hour, matching_minute = map(int, matching_time_str.split(':'))
        
        # Add jobs to scheduler
        for day in reminder_days:
            job_id = f'weekly_reminder_{day}'
            self.scheduler.add_job(
                self.send_weekly_reminder,
                CronTrigger(
                    day_of_week=day,
                    hour=reminder_hour,
                    minute=reminder_minute,
                    timezone=self.timezone
                ),
                id=job_id
            )

        for day in liking_days:
            job_id = f'send_liking_phase_{day}'
            self.scheduler.add_job(
                self.send_liking_phase_list,
                CronTrigger(
                    day_of_week=day,
                    hour=liking_hour,
                    minute=liking_minute,
                    timezone=self.timezone
                ),
                id=job_id
            )

        for day in matching_days:
            job_id = f'send_matches_{day}'
            self.scheduler.add_job(
                self.send_participant_list,
                CronTrigger(
                    day_of_week=day,
                    hour=matching_hour,
                    minute=matching_minute,
                    timezone=self.timezone
                ),
                id=job_id
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
