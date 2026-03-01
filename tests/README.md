# Habitz Test Suite

Unit and integration tests for the Habits Tracker backend and frontend.

## Backend Tests (Python/Pytest)

### Setup

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=landing --cov=shared

# Run specific test file
pytest tests/test_habits_api.py

# Run specific test class
pytest tests/test_habits_api.py::TestHabitToggle

# Run specific test
pytest tests/test_habits_api.py::TestHabitToggle::test_toggle_habit_creates_log
```

### Test Structure

#### `test_habits_api.py`

**TestHabitToggle**
- `test_toggle_habit_creates_log` - Verify toggling a habit creates a log entry
- `test_toggle_habit_with_date_parameter` - Verify date parameter support
- `test_toggle_habit_removes_log` - Verify toggling removes completed log
- `test_toggle_non_manual_habit_fails` - Verify non-manual habits can't be toggled

**TestHabitsCalendar**
- `test_calendar_returns_month_data` - Verify calendar endpoint returns month data
- `test_calendar_calculates_progress` - Verify completion progress calculation

**TestWeeklyStats**
- `test_weekly_returns_7_days` - Verify 7 days returned
- `test_weekly_identifies_today` - Verify today is correctly identified

**TestTimezoneHandling**
- `test_get_user_today_respects_timezone` - Verify timezone-aware date handling
- `test_user_timezone_defaults_to_new_york` - Verify default timezone
- `test_different_timezones_produce_different_dates` - Verify multi-timezone support

### Fixtures

- `app` - Test Flask application with in-memory SQLite
- `client` - Test client for making requests
- `user` - Single test user
- `user_with_habits` - User with 2 test habits
- `authenticated_client` - Pre-authenticated client and user

## Frontend Tests (JavaScript/Jest)

### Setup

```bash
# Install test dependencies
npm install --save-dev jest @testing-library/dom @testing-library/jest-dom

# Run all tests
npm test

# Run specific test file
npm test -- test_habits_frontend.js

# Run with coverage
npm test -- --coverage
```

### Test Structure

#### `test_habits_frontend.js`

**Date Navigation**
- `should disable next button when at today` - Verify button state
- `should allow navigation to past dates` - Verify navigation works
- `should format dates correctly` - Verify YYYY-MM-DD format

**Habit Progress Tracking**
- `should calculate progress percentage correctly` - Verify math
- `should update progress when habit is toggled` - Verify state updates
- `should prevent progress from exceeding total` - Verify bounds checking
- `should prevent negative progress` - Verify bounds checking

**Weekly Ring Rendering**
- `should render 7 days in weekly view` - Verify data structure
- `should calculate ring offset correctly` - Verify SVG calculations
- `should identify today correctly` - Verify date comparison

**Calendar Day Rendering**
- `should render correct number of days for month` - Verify day count
- `should mark completed days` - Verify CSS classes
- `should not mark incomplete days` - Verify CSS classes

**Habit Toggle API**
- `should send toggle request with date parameter` - Verify API call
- `should handle toggle response correctly` - Verify response handling
- `should handle network errors gracefully` - Verify error handling

## Running All Tests

```bash
# Backend
pytest tests/

# Frontend
npm test

# Both (if integrated CI setup)
pytest && npm test
```

## Coverage Goals

- **Backend**: Aim for >80% coverage on API endpoints and core logic
- **Frontend**: Aim for >70% coverage on user interactions and calculations

## Adding New Tests

1. **Backend**: Add test to appropriate class in `test_habits_api.py`
2. **Frontend**: Add test to appropriate describe block in `test_habits_frontend.js`
3. Run tests to verify they pass: `pytest` or `npm test`
4. Commit with test changes: `git commit -m "Add tests for feature X"`

## Continuous Integration

Tests should be run:
- Before commit (git hooks)
- On every pull request
- Before deployment

Example GitHub Actions:
```yaml
- name: Run backend tests
  run: pytest --cov

- name: Run frontend tests
  run: npm test -- --coverage
```
