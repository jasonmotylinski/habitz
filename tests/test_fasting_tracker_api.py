"""Tests for fasting tracker API endpoints."""
import pytest
from datetime import datetime, timedelta
from fasting_tracker.models import Fast
from shared import db
from shared.user import User


class TestFastCreation:
    """Tests for creating and starting fasts."""

    def test_create_fast(self, app, user):
        """Test creating a new fast."""
        with app.app_context():
            fast = Fast(
                user_id=user.id,
                target_hours=16,
                started_at=datetime.utcnow()
            )
            db.session.add(fast)
            db.session.commit()

            assert fast.id is not None
            assert fast.target_hours == 16
            assert fast.is_active is True
            assert fast.completed is False

    def test_fast_with_note(self, app, user):
        """Test creating a fast with a note."""
        with app.app_context():
            fast = Fast(
                user_id=user.id,
                target_hours=18,
                started_at=datetime.utcnow(),
                note='Starting after dinner'
            )
            db.session.add(fast)
            db.session.commit()

            assert fast.note == 'Starting after dinner'

    def test_user_default_fast_duration(self, app, user):
        """Test user has default fast duration."""
        with app.app_context():
            user = User.query.get(user.id)
            assert user.default_fast_hours == 16


class TestFastProgress:
    """Tests for fast progress calculations."""

    def test_fast_duration_calculation(self, app, user):
        """Test calculating elapsed time in fast."""
        with app.app_context():
            start = datetime.utcnow() - timedelta(hours=8)
            fast = Fast(
                user_id=user.id,
                target_hours=16,
                started_at=start
            )
            db.session.add(fast)
            db.session.commit()

            duration = fast.duration_seconds
            # Should be approximately 8 hours
            assert 28000 < duration < 29000  # 8 hours +/- some buffer

    def test_fast_progress_percentage(self, app, user):
        """Test calculating progress percentage."""
        with app.app_context():
            start = datetime.utcnow() - timedelta(hours=8)
            fast = Fast(
                user_id=user.id,
                target_hours=16,
                started_at=start
            )
            db.session.add(fast)
            db.session.commit()

            progress = fast.progress_pct
            # Should be 50% (8 hours out of 16)
            assert 45 < progress < 55

    def test_fast_target_seconds(self, app, user):
        """Test target seconds calculation."""
        with app.app_context():
            fast = Fast(
                user_id=user.id,
                target_hours=16,
                started_at=datetime.utcnow()
            )
            db.session.add(fast)
            db.session.commit()

            assert fast.target_seconds == 16 * 3600
            assert fast.target_seconds == 57600

    def test_fast_progress_capped_at_100(self, app, user):
        """Test that progress doesn't exceed 100%."""
        with app.app_context():
            start = datetime.utcnow() - timedelta(hours=20)
            fast = Fast(
                user_id=user.id,
                target_hours=16,
                started_at=start
            )
            db.session.add(fast)
            db.session.commit()

            progress = fast.progress_pct
            assert progress == 100.0

    def test_fast_remaining_seconds_when_active(self, app, user):
        """Test calculating remaining time for active fast."""
        with app.app_context():
            start = datetime.utcnow() - timedelta(hours=10)
            fast = Fast(
                user_id=user.id,
                target_hours=16,
                started_at=start
            )
            db.session.add(fast)
            db.session.commit()

            data = fast.to_dict()
            assert 'remaining_seconds' in data
            # Should have about 6 hours remaining
            assert 20000 < data['remaining_seconds'] < 22000


class TestFastCompletion:
    """Tests for completing fasts."""

    def test_complete_fast(self, app, user):
        """Test marking a fast as completed."""
        with app.app_context():
            start = datetime.utcnow() - timedelta(hours=16, minutes=30)
            fast = Fast(
                user_id=user.id,
                target_hours=16,
                started_at=start
            )
            db.session.add(fast)
            db.session.commit()

            # Complete the fast
            fast.ended_at = datetime.utcnow()
            fast.completed = True
            db.session.commit()

            updated = Fast.query.get(fast.id)
            assert updated.is_active is False
            assert updated.completed is True

    def test_fast_is_not_active_after_end(self, app, user):
        """Test that completed fast is not active."""
        with app.app_context():
            start = datetime.utcnow() - timedelta(hours=16)
            end = datetime.utcnow()
            fast = Fast(
                user_id=user.id,
                target_hours=16,
                started_at=start,
                ended_at=end,
                completed=True
            )
            db.session.add(fast)
            db.session.commit()

            assert fast.is_active is False

    def test_end_fast_early(self, app, user):
        """Test ending a fast before target time."""
        with app.app_context():
            start = datetime.utcnow() - timedelta(hours=8)
            fast = Fast(
                user_id=user.id,
                target_hours=16,
                started_at=start
            )
            db.session.add(fast)
            db.session.commit()

            # End early
            fast.ended_at = datetime.utcnow()
            fast.completed = False
            db.session.commit()

            data = fast.to_dict()
            assert data['completed'] is False
            assert 'ended_at' in data


class TestFastSerialization:
    """Tests for fast data serialization."""

    def test_fast_to_dict(self, app, user):
        """Test fast serialization to dict."""
        with app.app_context():
            start = datetime.utcnow()
            fast = Fast(
                user_id=user.id,
                target_hours=16,
                started_at=start,
                note='Test fast'
            )
            db.session.add(fast)
            db.session.commit()

            data = fast.to_dict()
            assert 'id' in data
            assert data['target_hours'] == 16
            assert data['completed'] is False
            assert 'remaining_seconds' in data
            assert data['note'] == 'Test fast'

    def test_completed_fast_to_dict(self, app, user):
        """Test completed fast serialization includes end time."""
        with app.app_context():
            start = datetime.utcnow() - timedelta(hours=16)
            end = datetime.utcnow()
            fast = Fast(
                user_id=user.id,
                target_hours=16,
                started_at=start,
                ended_at=end,
                completed=True
            )
            db.session.add(fast)
            db.session.commit()

            data = fast.to_dict()
            assert 'ended_at' in data
            assert 'remaining_seconds' not in data


class TestFastQueries:
    """Tests for fast queries and filtering."""

    def test_get_active_fasts(self, app, user):
        """Test querying for active fasts."""
        with app.app_context():
            # Create active fast
            active = Fast(
                user_id=user.id,
                target_hours=16,
                started_at=datetime.utcnow()
            )
            
            # Create completed fast
            completed = Fast(
                user_id=user.id,
                target_hours=16,
                started_at=datetime.utcnow() - timedelta(hours=20),
                ended_at=datetime.utcnow(),
                completed=True
            )
            
            db.session.add_all([active, completed])
            db.session.commit()

            # Query active fasts
            active_fasts = Fast.query.filter_by(
                user_id=user.id,
                ended_at=None
            ).all()
            
            assert len(active_fasts) == 1
            assert active_fasts[0].is_active is True

    def test_get_fast_history(self, app, user):
        """Test querying fast history."""
        with app.app_context():
            # Create multiple completed fasts
            for i in range(3):
                fast = Fast(
                    user_id=user.id,
                    target_hours=16 + i,
                    started_at=datetime.utcnow() - timedelta(days=i),
                    ended_at=datetime.utcnow() - timedelta(days=i) + timedelta(hours=16),
                    completed=True
                )
                db.session.add(fast)
            db.session.commit()

            # Get history
            history = Fast.query.filter_by(
                user_id=user.id,
                completed=True
            ).order_by(Fast.started_at.desc()).all()

            assert len(history) == 3
            assert history[0].target_hours == 16


class TestFastDifferentDurations:
    """Tests for various fast durations."""

    def test_12_hour_fast(self, app, user):
        """Test 12 hour fast."""
        with app.app_context():
            fast = Fast(
                user_id=user.id,
                target_hours=12,
                started_at=datetime.utcnow()
            )
            db.session.add(fast)
            db.session.commit()

            assert fast.target_seconds == 43200

    def test_24_hour_fast(self, app, user):
        """Test 24 hour fast."""
        with app.app_context():
            fast = Fast(
                user_id=user.id,
                target_hours=24,
                started_at=datetime.utcnow()
            )
            db.session.add(fast)
            db.session.commit()

            assert fast.target_seconds == 86400

    def test_custom_duration_fast(self, app, user):
        """Test custom duration fast."""
        with app.app_context():
            fast = Fast(
                user_id=user.id,
                target_hours=20,
                started_at=datetime.utcnow()
            )
            db.session.add(fast)
            db.session.commit()

            assert fast.target_seconds == 72000
