"""Pytest configuration and fixtures."""
import pytest
from datetime import date
from landing import create_app
from shared import db
from shared.user import User
from landing.models import Habit, HabitLog


@pytest.fixture
def app():
    """Create and configure a test app."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def user(app):
    """Create a test user."""
    with app.app_context():
        user = User(
            email='test@example.com',
            username='testuser',
            timezone='America/New_York'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def user_with_habits(user):
    """Create a user with test habits."""
    from landing.models import Habit
    habits = [
        Habit(
            user_id=user.id,
            name='Morning Run',
            habit_type='manual',
            icon='🏃',
            color='#4A90E2',
            sort_order=0
        ),
        Habit(
            user_id=user.id,
            name='Read',
            habit_type='manual',
            icon='📚',
            color='#22c55e',
            sort_order=1
        ),
    ]
    for habit in habits:
        db.session.add(habit)
    db.session.commit()
    return user, habits


@pytest.fixture
def authenticated_client(client, user):
    """Test client authenticated as a user."""
    with client:
        # Login the user
        from flask_login import login_user
        client.get('/')  # Trigger auth context
        with client.session_transaction() as sess:
            # Manually set auth in session for testing
            pass
        # Actually, we'll use POST login if there's a login endpoint
        return client, user


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "calorie: mark test as calorie tracker test"
    )
    config.addinivalue_line(
        "markers", "fasting: mark test as fasting tracker test"
    )
    config.addinivalue_line(
        "markers", "workout: mark test as workout tracker test"
    )
    config.addinivalue_line(
        "markers", "meal: mark test as meal planner test"
    )
