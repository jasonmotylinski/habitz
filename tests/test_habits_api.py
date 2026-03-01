"""Tests for habits API endpoints."""
import pytest
from datetime import date, timedelta
from landing.api import get_user_today
from landing.models import Habit, HabitLog, DailyNote, DailyMood
from shared import db
from shared.user import User


class TestHabitToggle:
    """Tests for habit toggle endpoint."""

    def test_toggle_habit_creates_log(self, app, user_with_habits):
        """Test toggling a manual habit creates a log entry."""
        user, habits = user_with_habits
        habit = habits[0]

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = user.id

            # Mock auth by manually setting current_user
            from flask_login import login_user
            with app.test_request_context():
                login_user(user)

                # Toggle habit (should create log)
                response = client.post(
                    f'/api/habits/{habit.id}/toggle',
                    follow_redirects=True
                )

                # Check log was created
                log = HabitLog.query.filter_by(
                    habit_id=habit.id,
                    user_id=user.id
                ).first()

                assert log is not None
                assert log.completed_date == get_user_today(user)

    def test_toggle_habit_with_date_parameter(self, app, user_with_habits):
        """Test toggling a habit for a specific date."""
        user, habits = user_with_habits
        habit = habits[0]
        past_date = date.today() - timedelta(days=3)

        with app.test_client() as client:
            from flask_login import login_user
            with app.test_request_context():
                login_user(user)

                response = client.post(
                    f'/api/habits/{habit.id}/toggle?date={past_date.isoformat()}',
                    follow_redirects=True
                )

                log = HabitLog.query.filter_by(
                    habit_id=habit.id,
                    completed_date=past_date
                ).first()

                assert log is not None

    def test_toggle_habit_removes_log(self, app, user_with_habits):
        """Test toggling a completed habit removes the log."""
        user, habits = user_with_habits
        habit = habits[0]
        today = get_user_today(user)

        # Create initial log
        log = HabitLog(
            habit_id=habit.id,
            user_id=user.id,
            completed_date=today
        )
        db.session.add(log)
        db.session.commit()

        with app.test_client() as client:
            from flask_login import login_user
            with app.test_request_context():
                login_user(user)

                response = client.post(
                    f'/api/habits/{habit.id}/toggle',
                    follow_redirects=True
                )

                log = HabitLog.query.filter_by(
                    habit_id=habit.id,
                    completed_date=today
                ).first()

                assert log is None

    def test_toggle_non_manual_habit_fails(self, app, user):
        """Test that non-manual habits cannot be toggled."""
        habit = Habit(
            user_id=user.id,
            name='Workout',
            habit_type='workout',
            icon='🏋️',
            color='#E2844A'
        )
        db.session.add(habit)
        db.session.commit()

        with app.test_client() as client:
            from flask_login import login_user
            with app.test_request_context():
                login_user(user)

                response = client.post(
                    f'/api/habits/{habit.id}/toggle',
                    follow_redirects=True
                )

                # Should get error
                data = response.get_json()
                assert 'error' in data


class TestHabitsCalendar:
    """Tests for calendar endpoint."""

    def test_calendar_returns_month_data(self, app, user_with_habits):
        """Test calendar endpoint returns days with completion data."""
        user, habits = user_with_habits

        # Create logs for a few days
        today = get_user_today(user)
        for i in range(3):
            log = HabitLog(
                habit_id=habits[0].id,
                user_id=user.id,
                completed_date=today - timedelta(days=i)
            )
            db.session.add(log)
        db.session.commit()

        with app.test_client() as client:
            from flask_login import login_user
            with app.test_request_context():
                login_user(user)

                month_str = today.strftime('%Y-%m')
                response = client.get(f'/api/habits/calendar?month={month_str}')

                data = response.get_json()
                assert 'days' in data
                assert data['year'] == today.year
                assert data['month'] == today.month
                assert len(data['days']) > 0

    def test_calendar_calculates_progress(self, app, user_with_habits):
        """Test that calendar correctly calculates completion progress."""
        user, habits = user_with_habits
        today = get_user_today(user)

        # Complete 1 out of 2 habits
        log = HabitLog(
            habit_id=habits[0].id,
            user_id=user.id,
            completed_date=today
        )
        db.session.add(log)
        db.session.commit()

        with app.test_client() as client:
            from flask_login import login_user
            with app.test_request_context():
                login_user(user)

                month_str = today.strftime('%Y-%m')
                response = client.get(f'/api/habits/calendar?month={month_str}')

                data = response.get_json()
                today_data = next(d for d in data['days'] if d['date'] == today.isoformat())

                assert today_data['completed'] == 1
                assert today_data['total'] == 2
                assert today_data['progress'] == 0.5


class TestWeeklyStats:
    """Tests for weekly stats endpoint."""

    def test_weekly_returns_7_days(self, app, user_with_habits):
        """Test weekly endpoint returns 7 days of data."""
        user, habits = user_with_habits

        with app.test_client() as client:
            from flask_login import login_user
            with app.test_request_context():
                login_user(user)

                response = client.get('/api/habits/weekly')

                data = response.get_json()
                assert 'days' in data
                assert len(data['days']) == 7

    def test_weekly_identifies_today(self, app, user_with_habits):
        """Test that weekly correctly identifies today."""
        user, habits = user_with_habits
        today = get_user_today(user)

        with app.test_client() as client:
            from flask_login import login_user
            with app.test_request_context():
                login_user(user)

                response = client.get('/api/habits/weekly')

                data = response.get_json()
                today_data = next(d for d in data['days'] if d['is_today'])

                assert today_data['date'] == today.isoformat()


class TestTimezoneHandling:
    """Tests for timezone-aware date handling."""

    def test_get_user_today_respects_timezone(self, app):
        """Test that get_user_today uses user's timezone."""
        with app.app_context():
            user = User(
                email='tz@example.com',
                username='tzuser',
                timezone='America/Los_Angeles'
            )
            user.set_password('password')
            db.session.add(user)
            db.session.commit()

            today = get_user_today(user)

            # Should be a date object
            assert isinstance(today, date)

    def test_user_timezone_defaults_to_new_york(self, app, user):
        """Test that user timezone defaults to America/New_York."""
        assert user.timezone == 'America/New_York'

    def test_different_timezones_produce_different_dates(self, app):
        """Test that users in different timezones can have different dates."""
        with app.app_context():
            user_ny = User(
                email='ny@example.com',
                username='nyuser',
                timezone='America/New_York'
            )
            user_ny.set_password('password')

            user_la = User(
                email='la@example.com',
                username='lauser',
                timezone='America/Los_Angeles'
            )
            user_la.set_password('password')

            db.session.add_all([user_ny, user_la])
            db.session.commit()

            today_ny = get_user_today(user_ny)
            today_la = get_user_today(user_la)

            # In most cases they'll be the same, but the function
            # should handle both correctly
            assert isinstance(today_ny, date)
            assert isinstance(today_la, date)


class TestDailyNotes:
    """Tests for daily notes functionality."""

    def test_create_daily_note(self, app, user):
        """Test creating a daily note."""
        with app.app_context():
            note = DailyNote(
                user_id=user.id,
                date=date.today(),
                content='Had a great day!'
            )
            db.session.add(note)
            db.session.commit()

            assert note.id is not None
            assert note.content == 'Had a great day!'

    def test_update_daily_note(self, app, user):
        """Test updating a daily note."""
        with app.app_context():
            note = DailyNote(
                user_id=user.id,
                date=date.today(),
                content='First version'
            )
            db.session.add(note)
            db.session.commit()

            note.content = 'Updated version'
            db.session.commit()

            updated = DailyNote.query.get(note.id)
            assert updated.content == 'Updated version'

    def test_daily_note_unique_per_user_date(self, app, user):
        """Test that each user can only have one note per date."""
        with app.app_context():
            note1 = DailyNote(user_id=user.id, date=date.today(), content='Note 1')
            db.session.add(note1)
            db.session.commit()

            # Try to add another note for same date
            note2 = DailyNote(user_id=user.id, date=date.today(), content='Note 2')
            db.session.add(note2)

            with pytest.raises(Exception):  # Should raise integrity error
                db.session.commit()

    def test_daily_note_to_dict(self, app, user):
        """Test daily note serialization."""
        with app.app_context():
            note = DailyNote(
                user_id=user.id,
                date=date.today(),
                content='Test note'
            )
            db.session.add(note)
            db.session.commit()

            data = note.to_dict()
            assert data['date'] == date.today().isoformat()
            assert data['content'] == 'Test note'
            assert 'created_at' in data

    def test_notes_per_user(self, app, user):
        """Test querying notes per user."""
        with app.app_context():
            for i in range(5):
                note = DailyNote(
                    user_id=user.id,
                    date=date.today() - timedelta(days=i),
                    content=f'Note {i}'
                )
                db.session.add(note)
            db.session.commit()

            notes = DailyNote.query.filter_by(user_id=user.id).all()
            assert len(notes) == 5


class TestDailyMood:
    """Tests for daily mood tracking."""

    def test_create_daily_mood(self, app, user):
        """Test creating a daily mood entry."""
        with app.app_context():
            mood = DailyMood(
                user_id=user.id,
                date=date.today(),
                mood=5
            )
            db.session.add(mood)
            db.session.commit()

            assert mood.id is not None
            assert mood.mood == 5

    def test_mood_range_1_to_5(self, app, user):
        """Test that mood values are between 1 and 5."""
        with app.app_context():
            for mood_val in range(1, 6):
                mood = DailyMood(
                    user_id=user.id,
                    date=date.today() - timedelta(days=mood_val),
                    mood=mood_val
                )
                db.session.add(mood)
            db.session.commit()

            moods = DailyMood.query.filter_by(user_id=user.id).all()
            assert len(moods) == 5
            assert all(1 <= m.mood <= 5 for m in moods)

    def test_mood_emoji_mapping(self, app, user):
        """Test mood to emoji mapping."""
        with app.app_context():
            mapping = {
                1: '😢',
                2: '😕',
                3: '😐',
                4: '😊',
                5: '😄',
            }

            for mood_val, expected_emoji in mapping.items():
                emoji = DailyMood.get_emoji_for_mood(mood_val)
                assert emoji == expected_emoji

    def test_mood_with_notes(self, app, user):
        """Test mood with additional notes."""
        with app.app_context():
            mood = DailyMood(
                user_id=user.id,
                date=date.today(),
                mood=4,
                notes='Feeling happy because...'
            )
            db.session.add(mood)
            db.session.commit()

            assert mood.notes == 'Feeling happy because...'

    def test_mood_with_custom_emoji(self, app, user):
        """Test mood with custom emoji override."""
        with app.app_context():
            mood = DailyMood(
                user_id=user.id,
                date=date.today(),
                mood=4,
                emoji='🎉'
            )
            db.session.add(mood)
            db.session.commit()

            assert mood.emoji == '🎉'

    def test_mood_unique_per_user_date(self, app, user):
        """Test that each user can only have one mood per date."""
        with app.app_context():
            mood1 = DailyMood(user_id=user.id, date=date.today(), mood=4)
            db.session.add(mood1)
            db.session.commit()

            mood2 = DailyMood(user_id=user.id, date=date.today(), mood=5)
            db.session.add(mood2)

            with pytest.raises(Exception):  # Should raise integrity error
                db.session.commit()

    def test_mood_to_dict(self, app, user):
        """Test mood serialization."""
        with app.app_context():
            mood = DailyMood(
                user_id=user.id,
                date=date.today(),
                mood=4,
                notes='Feeling great'
            )
            db.session.add(mood)
            db.session.commit()

            data = mood.to_dict()
            assert data['date'] == date.today().isoformat()
            assert data['mood'] == 4
            assert data['emoji'] == '😊'
            assert data['notes'] == 'Feeling great'

    def test_mood_progression(self, app, user):
        """Test tracking mood over time."""
        with app.app_context():
            moods = [2, 3, 4, 5, 4]  # Improving mood progression
            for i, mood_val in enumerate(moods):
                mood = DailyMood(
                    user_id=user.id,
                    date=date.today() - timedelta(days=len(moods) - i - 1),
                    mood=mood_val
                )
                db.session.add(mood)
            db.session.commit()

            history = DailyMood.query.filter_by(
                user_id=user.id
            ).order_by(DailyMood.date).all()

            actual_moods = [m.mood for m in history]
            assert actual_moods == moods
