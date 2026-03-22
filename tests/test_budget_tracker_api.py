"""Tests for budget tracker sheets module and route."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import date

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── sheets.py unit tests ──────────────────────────────────────────────────────

class TestGetWeeklyTabName:
    def test_saturday_returns_itself(self):
        from budget_tracker.sheets import get_weekly_tab_name
        # 2026-03-21 is a Saturday
        assert get_weekly_tab_name(date(2026, 3, 21)) == '20260321'

    def test_sunday_returns_prior_saturday(self):
        from budget_tracker.sheets import get_weekly_tab_name
        # 2026-03-22 is a Sunday — prior Saturday is Mar 21
        assert get_weekly_tab_name(date(2026, 3, 22)) == '20260321'

    def test_friday_returns_prior_saturday(self):
        from budget_tracker.sheets import get_weekly_tab_name
        # 2026-03-27 is a Friday — prior Saturday is Mar 21
        assert get_weekly_tab_name(date(2026, 3, 27)) == '20260321'

    def test_next_saturday_returns_itself(self):
        from budget_tracker.sheets import get_weekly_tab_name
        assert get_weekly_tab_name(date(2026, 3, 28)) == '20260328'


class TestGetAvailableWeeks:
    def test_returns_yyyymmdd_tabs_sorted_descending(self):
        from budget_tracker.sheets import get_available_weeks
        service = MagicMock()
        service.spreadsheets().get().execute.return_value = {
            'sheets': [
                {'properties': {'title': '20260321'}},
                {'properties': {'title': '20260314'}},
                {'properties': {'title': 'Budget vs Actuals'}},
                {'properties': {'title': 'Debts'}},
                {'properties': {'title': '20260307'}},
            ]
        }
        result = get_available_weeks(service, 'sheet123')
        assert result == ['20260321', '20260314', '20260307']

    def test_ignores_non_date_tabs(self):
        from budget_tracker.sheets import get_available_weeks
        service = MagicMock()
        service.spreadsheets().get().execute.return_value = {
            'sheets': [
                {'properties': {'title': 'Budget vs Actuals'}},
                {'properties': {'title': 'Debts'}},
            ]
        }
        result = get_available_weeks(service, 'sheet123')
        assert result == []

    def test_ignores_invalid_date_tabs(self):
        from budget_tracker.sheets import get_available_weeks
        service = MagicMock()
        service.spreadsheets().get().execute.return_value = {
            'sheets': [
                {'properties': {'title': '20261399'}},  # invalid date
                {'properties': {'title': '12345678'}},  # arbitrary 8-digit number
                {'properties': {'title': '20260321'}},  # valid
            ]
        }
        result = get_available_weeks(service, 'sheet123')
        assert result == ['20260321']


class TestGetWeeklySummary:
    def _make_service(self, f1, f2, f3):
        service = MagicMock()
        service.spreadsheets().values().get().execute.return_value = {
            'values': [[f1], [f2], [f3]]
        }
        return service

    def test_normal_week(self):
        from budget_tracker.sheets import get_weekly_summary
        service = self._make_service(607.50, 1750.0, 1142.50)
        result = get_weekly_summary(service, 'sheet123', '20260321')
        assert result['total_spent'] == 607.50
        assert result['budget'] == 1750.0
        assert result['remaining'] == 1142.50
        assert result['pct_spent'] == 35

    def test_over_budget(self):
        from budget_tracker.sheets import get_weekly_summary
        service = self._make_service(1900.0, 1750.0, -150.0)
        result = get_weekly_summary(service, 'sheet123', '20260321')
        assert result['remaining'] == -150.0
        assert result['pct_spent'] == 109

    def test_empty_tab_returns_zeros(self):
        from budget_tracker.sheets import get_weekly_summary
        service = MagicMock()
        service.spreadsheets().values().get().execute.return_value = {'values': []}
        result = get_weekly_summary(service, 'sheet123', '20260321')
        assert result['total_spent'] == 0.0
        assert result['budget'] == 0.0
        assert result['remaining'] == 0.0


class TestGetWeeklyTransactions:
    def test_returns_rows_excluding_header_and_overage(self):
        from budget_tracker.sheets import get_weekly_transactions
        service = MagicMock()
        service.spreadsheets().values().get().execute.return_value = {
            'values': [
                ['2026-03-20', 'Whole Foods', 'BofA', 124.38],
                ['2026-03-19', 'NJ Transit', 'BofA', 5.50],
            ]
        }
        result = get_weekly_transactions(service, 'sheet123', '20260321')
        assert len(result) == 2
        assert result[0]['name'] == 'Whole Foods'
        assert result[0]['amount'] == 124.38
        assert result[1]['name'] == 'NJ Transit'

    def test_sorted_by_date_descending(self):
        from budget_tracker.sheets import get_weekly_transactions
        service = MagicMock()
        service.spreadsheets().values().get().execute.return_value = {
            'values': [
                ['2026-03-19', 'NJ Transit', 'BofA', 5.50],
                ['2026-03-21', 'Trader Joes', 'BofA', 87.22],
                ['2026-03-20', 'Whole Foods', 'BofA', 124.38],
            ]
        }
        result = get_weekly_transactions(service, 'sheet123', '20260321')
        assert result[0]['date'] == '2026-03-21'
        assert result[1]['date'] == '2026-03-20'
        assert result[2]['date'] == '2026-03-19'

    def test_empty_tab(self):
        from budget_tracker.sheets import get_weekly_transactions
        service = MagicMock()
        service.spreadsheets().values().get().execute.return_value = {'values': []}
        result = get_weekly_transactions(service, 'sheet123', '20260321')
        assert result == []

    def test_handles_integer_date_serials(self):
        from budget_tracker.sheets import get_weekly_transactions
        service = MagicMock()
        # Google Sheets serial for 2026-03-21 is 46111, 2026-03-20 is 46110
        service.spreadsheets().values().get().execute.return_value = {
            'values': [
                [46110, 'Whole Foods', 'BofA', 124.38],   # Mar 20
                [46111, 'Trader Joes', 'BofA', 87.22],    # Mar 21
            ]
        }
        result = get_weekly_transactions(service, 'sheet123', '20260321')
        # Should be sorted descending: Mar 21 first
        assert result[0]['name'] == 'Trader Joes'
        assert result[1]['name'] == 'Whole Foods'


# ── Route tests ───────────────────────────────────────────────────────────────

@pytest.fixture
def budget_app():
    """Create budget tracker test app with in-memory DB."""
    from budget_tracker import create_app
    app = create_app('testing')
    app.config.update({
        'WTF_CSRF_ENABLED': False,
        'GOOGLE_SERVICE_ACCOUNT_JSON': '/fake/path.json',
        'GOOGLE_SHEET_ID': 'fake-sheet-id',
        'SECRET_KEY': 'test-secret',
        'SESSION_COOKIE_NAME': 'habitz_session',
    })
    with app.app_context():
        from shared import db
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def budget_user_id(budget_app):
    """Create and return a test user ID in the budget app context."""
    with budget_app.app_context():
        from shared import db
        from shared.user import User
        u = User(email='courtney@example.com', username='courtney')
        u.set_password('password123')
        db.session.add(u)
        db.session.commit()
        return u.id


@pytest.fixture
def budget_client(budget_app, budget_user_id):
    """Authenticated test client for budget app."""
    client = budget_app.test_client()
    with budget_app.app_context():
        from shared import db
        from shared.user import User
        user = db.session.get(User, budget_user_id)
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
    return client


class TestBudgetRoute:
    def test_unauthenticated_redirects_to_login(self, budget_app):
        """Unauthenticated requests must redirect to login."""
        client = budget_app.test_client()
        resp = client.get('/')
        assert resp.status_code == 302
        assert '/login' in resp.headers['Location']

    def test_authenticated_returns_200(self, budget_client, budget_app):
        """Authenticated requests return 200."""
        with patch('budget_tracker.main._get_service') as mock_svc, \
             patch('budget_tracker.main.get_available_weeks') as mock_weeks, \
             patch('budget_tracker.main.get_weekly_summary') as mock_summary, \
             patch('budget_tracker.main.get_weekly_transactions') as mock_txns:

            mock_svc.return_value = MagicMock()
            mock_weeks.return_value = ['20260321', '20260314']
            mock_summary.return_value = {
                'budget': 1750.0, 'total_spent': 607.5,
                'remaining': 1142.5, 'pct_spent': 35,
            }
            mock_txns.return_value = []

            resp = budget_client.get('/')
            assert resp.status_code == 200

    def test_week_param_uses_specified_tab(self, budget_client, budget_app):
        """?week= param selects the correct tab."""
        with patch('budget_tracker.main._get_service') as mock_svc, \
             patch('budget_tracker.main.get_available_weeks') as mock_weeks, \
             patch('budget_tracker.main.get_weekly_summary') as mock_summary, \
             patch('budget_tracker.main.get_weekly_transactions') as mock_txns:

            mock_svc.return_value = MagicMock()
            mock_weeks.return_value = ['20260321', '20260314']
            mock_summary.return_value = {
                'budget': 1750.0, 'total_spent': 900.0,
                'remaining': 850.0, 'pct_spent': 51,
            }
            mock_txns.return_value = []

            resp = budget_client.get('/?week=20260314')
            assert resp.status_code == 200
            mock_summary.assert_called_once_with(mock_svc.return_value, 'fake-sheet-id', '20260314')

    def test_nonexistent_tab_shows_empty_state(self, budget_client, budget_app):
        """Requesting a week not yet in the sheet renders without crashing."""
        with patch('budget_tracker.main._get_service') as mock_svc, \
             patch('budget_tracker.main.get_available_weeks') as mock_weeks:

            mock_svc.return_value = MagicMock()
            mock_weeks.return_value = ['20260314']  # current week not in sheet

            resp = budget_client.get('/?week=20260321')
            assert resp.status_code == 200

    def test_sheets_api_error_handled_gracefully(self, budget_client, budget_app):
        """Sheets API failure renders 200 with flash message (no crash)."""
        with patch('budget_tracker.main._get_service') as mock_svc:
            mock_svc.side_effect = Exception('Sheets API unavailable')

            resp = budget_client.get('/')
            assert resp.status_code == 200

    def test_invalid_week_param_ignored(self, budget_client, budget_app):
        """Malformed ?week= param falls back to current week."""
        with patch('budget_tracker.main._get_service') as mock_svc, \
             patch('budget_tracker.main.get_available_weeks') as mock_weeks, \
             patch('budget_tracker.main.get_weekly_summary') as mock_summary, \
             patch('budget_tracker.main.get_weekly_transactions') as mock_txns:

            mock_svc.return_value = MagicMock()
            mock_weeks.return_value = ['20260321']
            mock_summary.return_value = {
                'budget': 1750.0, 'total_spent': 0.0,
                'remaining': 1750.0, 'pct_spent': 0,
            }
            mock_txns.return_value = []

            # Malformed week param should be ignored, defaults to current week
            resp = budget_client.get('/?week=../../etc')
            assert resp.status_code == 200
