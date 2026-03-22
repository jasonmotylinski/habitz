"""Tests for fasting tracker API endpoints."""
import pytest
from datetime import datetime, timedelta
from fasting_tracker.models import Fast, MicroFast
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


# ---------------------------------------------------------------------------
# Micro fast HTTP API tests
# ---------------------------------------------------------------------------

@pytest.fixture
def fasting_app():
    """Create a fasting tracker Flask app for HTTP testing."""
    import os
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

    # Import all models BEFORE create_app so that the household table is
    # registered in SQLAlchemy metadata before db.create_all() runs inside
    # fasting_tracker's create_app (User.household_id FK requires it).
    import meal_planner.models     # noqa: F401
    import workout_tracker.models  # noqa: F401
    import calorie_tracker.models  # noqa: F401
    import fasting_tracker.models  # noqa: F401
    import landing.models          # noqa: F401

    from fasting_tracker import create_app
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_ECHO'] = False

    with app.app_context():
        db.session.configure(expire_on_commit=False)
        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def fasting_user(fasting_app):
    """Create a test user in the fasting tracker app."""
    with fasting_app.app_context():
        user = User(
            email='fasting@example.com',
            username='fastinguser',
            timezone='America/New_York',
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        db.session.expunge(user)
        return user


@pytest.fixture
def fasting_client(fasting_app, fasting_user):
    """Authenticated test client for the fasting tracker app."""
    client = fasting_app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(fasting_user.id)
    return client, fasting_user


class TestMicroFastAPI:
    """HTTP API tests for micro fast endpoints."""

    def test_start_micro_fast(self, fasting_app, fasting_client):
        """POST /api/micro/start returns 201 with id and default target_minutes=180."""
        client, user = fasting_client
        resp = client.post('/api/micro/start', json={})
        assert resp.status_code == 201
        data = resp.get_json()
        assert 'id' in data
        assert data['target_minutes'] == 180
        # Active fast: no ended_at in response
        assert 'ended_at' not in data

    def test_start_micro_fast_with_label_and_target(self, fasting_app, fasting_client):
        """POST /api/micro/start with label and target_minutes stores them correctly."""
        client, user = fasting_client
        resp = client.post('/api/micro/start', json={
            'label': 'lunch-dinner',
            'target_minutes': 210,
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['label'] == 'lunch-dinner'
        assert data['target_minutes'] == 210

    def test_start_micro_fast_conflict(self, fasting_app, fasting_client):
        """Starting a second micro fast while one is active returns 400."""
        client, user = fasting_client
        client.post('/api/micro/start', json={})
        resp = client.post('/api/micro/start', json={})
        assert resp.status_code == 400

    def test_stop_micro_fast(self, fasting_app, fasting_client):
        """POST /api/micro/stop ends the active micro fast; completed=False for instant stop."""
        client, user = fasting_client
        client.post('/api/micro/start', json={})
        resp = client.post('/api/micro/stop')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'ended_at' in data
        # 0 elapsed << 180-minute target → not completed
        assert data['completed'] is False

    def test_stop_micro_fast_no_active(self, fasting_app, fasting_client):
        """POST /api/micro/stop with no active micro fast returns 400."""
        client, user = fasting_client
        resp = client.post('/api/micro/stop')
        assert resp.status_code == 400

    def test_active_micro_fast(self, fasting_app, fasting_client):
        """GET /api/micro/active returns the active fast, then null after stopping."""
        client, user = fasting_client
        start_resp = client.post('/api/micro/start', json={})
        mf_id = start_resp.get_json()['id']

        resp = client.get('/api/micro/active')
        assert resp.status_code == 200
        active_data = resp.get_json()
        assert active_data is not None
        assert active_data['id'] == mf_id

        client.post('/api/micro/stop')

        resp2 = client.get('/api/micro/active')
        assert resp2.status_code == 200
        assert resp2.get_json() is None

    def test_today_micro_fasts(self, fasting_app, fasting_client):
        """GET /api/micro/today returns a list containing the stopped fast."""
        client, user = fasting_client
        client.post('/api/micro/start', json={})
        client.post('/api/micro/stop')

        resp = client.get('/api/micro/today')
        assert resp.status_code == 200
        items = resp.get_json()
        assert isinstance(items, list)
        assert len(items) == 1

    def test_today_micro_fasts_utc_midnight_regression(self, fasting_app, fasting_client):
        """Micro fasts started near UTC midnight appear in /api/micro/today for the user's local date.

        Regression: func.date(started_at) compared UTC date to local date, causing fasts
        started after UTC midnight (but before local midnight, e.g. 20:11 NY / 00:11 UTC next day)
        to disappear from today's list.
        """
        from zoneinfo import ZoneInfo
        from datetime import timezone as dt_timezone

        client, user = fasting_client

        with fasting_app.app_context():
            from fasting_tracker.models import MicroFast
            tz = ZoneInfo('America/New_York')
            # Simulate a fast started at 20:00 NY time = 01:00 UTC next calendar day
            # e.g. local date is March 21, UTC date is March 22
            local_8pm = datetime(2026, 3, 21, 20, 0, 0, tzinfo=tz)
            utc_started = local_8pm.astimezone(dt_timezone.utc).replace(tzinfo=None)
            utc_ended = utc_started + timedelta(minutes=30)

            mf = MicroFast(
                user_id=user.id,
                started_at=utc_started,
                ended_at=utc_ended,
            )
            db.session.add(mf)
            db.session.commit()

        resp = client.get('/api/micro/today')
        assert resp.status_code == 200
        items = resp.get_json()
        # The fast started at 20:00 NY (March 21) must appear when today_local is March 21
        ids = [item['id'] for item in items]
        with fasting_app.app_context():
            from fasting_tracker.models import MicroFast as MF
            inserted = MF.query.filter(MF.user_id == user.id, MF.ended_at.isnot(None)).first()
            assert inserted.id in ids, (
                "Fast started at 20:00 NY (past UTC midnight) should appear in today's list"
            )

    def test_delete_micro_fast(self, fasting_app, fasting_client):
        """DELETE /api/micro/<id> removes a stopped micro fast."""
        client, user = fasting_client
        start_resp = client.post('/api/micro/start', json={})
        mf_id = start_resp.get_json()['id']
        client.post('/api/micro/stop')

        del_resp = client.delete(f'/api/micro/{mf_id}')
        assert del_resp.status_code == 200
        assert del_resp.get_json() == {'ok': True}

        today_resp = client.get('/api/micro/today')
        items = today_resp.get_json()
        assert all(item['id'] != mf_id for item in items)

    def test_delete_active_micro_fast_blocked(self, fasting_app, fasting_client):
        """DELETE on an active micro fast returns 400."""
        client, user = fasting_client
        start_resp = client.post('/api/micro/start', json={})
        mf_id = start_resp.get_json()['id']

        resp = client.delete(f'/api/micro/{mf_id}')
        assert resp.status_code == 400

    def test_update_micro_goal(self, fasting_app, fasting_client):
        """PUT /api/user/micro-goal updates default_micro_fast_minutes."""
        client, user = fasting_client
        resp = client.put('/api/user/micro-goal', json={
            'default_micro_fast_minutes': 240,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['default_micro_fast_minutes'] == 240
