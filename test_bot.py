#!/usr/bin/env python3
"""
Unit tests for SocialChatBot core functionality.
The tests avoid hitting Telegram by exercising internal helpers only.
"""

import asyncio
import sqlite3
import tempfile
import unittest
from pathlib import Path

from bot import SocialChatBot
from messages import TEXT


class TestableSocialChatBot(SocialChatBot):
    """Subclass that redirects the database to a temporary path."""

    def __init__(self, bot_token: str, config: dict, db_path: Path):
        self._custom_db_path = Path(db_path)
        super().__init__(bot_token, config)

    def _init_database(self):
        self.db_path = self._custom_db_path
        super()._init_database()


class SocialChatBotTestCase(unittest.TestCase):
    """Covers scheduling config parsing and key phase behaviors."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "bot_data.db"
        config = {
            "reminder_days": [0],
            "reminder_time": "09:00",
            "liking_days": [1],
            "liking_time": "10:00",
            "matching_days": [2],
            "matching_time": "11:00",
            "timezone": "UTC",
            "admin_ids": [],
        }
        self.bot = TestableSocialChatBot("TEST_TOKEN", config, self.db_path)
        self.bot._reset_current_week_participation()

    def tearDown(self):
        try:
            if self.bot.scheduler.state != 0:
                self.bot.scheduler.shutdown(wait=False)
        except Exception:
            pass
        self.temp_dir.cleanup()

    def test_normalize_days_filters_invalid_values(self):
        days = self.bot._normalize_days([0, 6, 7, -1, "2"], 3)
        self.assertEqual(days, [0, 6, 2])

        fallback_days = self.bot._normalize_days("bad", 4)
        self.assertEqual(fallback_days, [4])

    def test_parse_time_config_handles_invalid(self):
        hour, minute = self.bot._parse_time_config("25:61", "08:30", "reminder_time")
        self.assertEqual((hour, minute), (8, 30))

        with self.assertRaises(ValueError):
            self.bot._parse_time_config(None, None, "liking_time")

    def test_opt_in_and_auto_likes(self):
        self.bot._add_user(1, "alpha", "Alpha", 100)
        self.bot._add_user(2, "beta", "Beta", 200)

        self.bot._set_user_participation(1, True)
        self.assertEqual(len(self.bot._get_participants()), 1)

        self.bot._set_user_participation(2, True)
        participants = self.bot._get_participants()
        self.assertEqual({p["user_id"] for p in participants}, {1, 2})

        likes_user1 = self.bot._get_user_likes(1)
        likes_user2 = self.bot._get_user_likes(2)
        self.assertEqual(likes_user1, {2})
        self.assertEqual(likes_user2, {1})

    def test_matching_message_without_partners(self):
        self.bot._add_user(1, "solo", "Solo", 300)
        self.bot._set_user_participation(1, True)
        self.bot._set_week_phase("liking")

        message = self.bot._build_matching_phase_message(1)
        self.assertEqual(message, TEXT["matching_no_participants"])

    def test_send_participant_list_requires_two_participants(self):
        self.bot._add_user(1, "only", "Only", 400)
        self.bot._set_user_participation(1, True)
        self.bot._set_week_phase("liking")

        result = asyncio.run(self.bot.send_participant_list())
        self.assertEqual(result, 0)
        self.assertNotEqual(self.bot._get_week_phase(), "matching")


if __name__ == "__main__":
    unittest.main()
