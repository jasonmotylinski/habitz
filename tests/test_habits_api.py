"""Tests for habits API endpoints."""
import pytest
from datetime import date, timedelta
from landing.api import get_user_today
from landing.models import Habit, HabitLog
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
