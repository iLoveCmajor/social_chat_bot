#!/usr/bin/env python3
"""
Test script to verify bot functionality without requiring a live Telegram connection.
"""

import sys
import sqlite3
from pathlib import Path

def test_database_initialization():
    """Test that the database structure can be created correctly."""
    print("Testing database initialization...")
    
    # Import the bot module
    sys.path.insert(0, str(Path(__file__).parent))
    from bot import SocialChatBot
    
    # Create a test config
    test_config = {
        'reminder_day': 0,
        'reminder_time': '09:00',
        'matching_day': 0,
        'matching_time': '12:00'
    }
    
    # Create bot instance with dummy token
    bot = SocialChatBot("TEST_TOKEN", test_config)
    
    # Verify database was created
    assert bot.db_path.exists(), "Database file was not created"
    print("✓ Database file created")
    
    # Verify tables exist
    conn = sqlite3.connect(bot.db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    assert 'users' in tables, "Users table not created"
    print("✓ Users table exists")
    
    assert 'weekly_participation' in tables, "Weekly participation table not created"
    print("✓ Weekly participation table exists")

    assert 'weekly_dislikes' in tables, "Weekly dislikes table not created"
    print("✓ Weekly dislikes table exists")
    
    # Verify table schemas
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [row[1] for row in cursor.fetchall()]
    expected_user_cols = ['user_id', 'username', 'first_name', 'chat_id', 'is_active']
    
    for col in expected_user_cols:
        assert col in user_columns, f"Column {col} not in users table"
    print(f"✓ Users table has correct columns: {user_columns}")
    
    cursor.execute("PRAGMA table_info(weekly_participation)")
    participation_columns = [row[1] for row in cursor.fetchall()]
    expected_participation_cols = ['id', 'user_id', 'week_year', 'opted_in', 'timestamp']
    
    for col in expected_participation_cols:
        assert col in participation_columns, f"Column {col} not in weekly_participation table"
    print(f"✓ Weekly participation table has correct columns: {participation_columns}")
    
    conn.close()
    
    # Test adding a user
    print("\nTesting user operations...")
    bot._add_user(12345, "testuser", "Test User", 67890)
    
    conn = sqlite3.connect(bot.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = 12345")
    user = cursor.fetchone()
    conn.close()
    
    assert user is not None, "User was not added to database"
    assert user[1] == "testuser", "Username not stored correctly"
    print(f"✓ User added successfully: {user}")
    
    # Test setting participation
    print("\nTesting participation operations...")
    bot._set_user_participation(12345, True)
    
    conn = sqlite3.connect(bot.db_path)
    cursor = conn.cursor()
    week = bot._get_current_week()
    cursor.execute("SELECT * FROM weekly_participation WHERE user_id = 12345 AND week_year = ?", (week,))
    participation = cursor.fetchone()
    conn.close()
    
    assert participation is not None, "Participation record not created"
    assert participation[3] == 1, "Opted in status not set correctly"
    print(f"✓ Participation set successfully: {participation}")
    
    # Test getting participants
    print("\nTesting participant retrieval...")
    participants = bot._get_participants()
    assert len(participants) == 1, "Should have exactly one participant"
    assert participants[0]['user_id'] == 12345, "Wrong participant retrieved"
    print(f"✓ Participants retrieved successfully: {len(participants)} participants")
    
    # Test opt out
    bot._set_user_participation(12345, False)
    participants = bot._get_participants()
    assert len(participants) == 0, "Should have no participants after opt out"
    print("✓ Opt out works correctly")
    
    # Test getting all active users
    print("\nTesting active user retrieval...")
    active_users = bot._get_all_active_users()
    assert len(active_users) == 1, "Should have one active user"
    print(f"✓ Active users retrieved: {len(active_users)} users")

    print("\nTesting weekly pairing logic...")
    bot._reset_current_week_participation()

    match_users = [
        (20001, "match_a", "Match A", 90001),
        (20002, "match_b", "Match B", 90002),
        (20003, "match_c", "Match C", 90003),
        (20004, "match_d", "Match D", 90004),
        (20005, "match_e", "Match E", 90005),
    ]

    for user_id, username, first_name, chat_id in match_users:
        bot._add_user(user_id, username, first_name, chat_id)
        bot._set_user_participation(user_id, True)

    likes_for_a = bot._get_user_likes(20001)
    assert likes_for_a.issuperset({20002, 20003, 20004, 20005}), "Newly opted-in users should auto-like everyone"
    print("✓ Auto-like on opt-in covers all participants")

    bot._set_dislike_status(20001, 20002, True)
    likes_for_a = bot._get_user_likes(20001)
    assert 20002 not in likes_for_a, "Dislike should remove like record"
    dislikes_for_a = bot._get_user_dislikes(20001)
    assert 20002 in dislikes_for_a, "Dislike state should be tracked"
    bot._set_dislike_status(20001, 20002, False)
    assert 20002 in bot._get_user_likes(20001), "Removing dislike should restore like"
    print("✓ Dislike toggles update likes/dislikes correctly")

    participants = bot._get_participants()
    participant_lookup = {p['user_id']: p for p in participants}
    matches = bot._generate_weekly_pairings(participant_lookup)

    assert matches[20001] == 20002, "match_a should pair with match_b"
    assert matches[20002] == 20001, "match_b should pair with match_a"
    assert matches[20003] == 20004, "match_c should pair with match_d"
    assert matches[20004] == 20003, "match_d should pair with match_c"
    assert matches[20005] is None, "match_e should remain unmatched"
    print("✓ Weekly pairing logic generates disjoint pairs with leftovers")

    print("\nTesting matching phase gating...")
    assert not bot._is_matching_phase_active(), "Matching phase should be inactive by default"
    bot._start_matching_phase()
    assert bot._is_matching_phase_active(), "Matching phase should be active after start"
    assert bot._set_like_status(20005, 20001, True) is False, "Likes should be locked once matching starts"
    print("✓ Matching phase prevents further liking actions")

    # Clean up test database
    bot.db_path.unlink()
    print(f"\n✓ Test database cleaned up")
    
    print("\n✅ All tests passed!")


if __name__ == '__main__':
    try:
        test_database_initialization()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
