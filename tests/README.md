# Habitz Test Suite

Comprehensive unit and integration tests for all four Habitz trackers (Habits, Calorie, Fasting, Workout, Meal Planner).

## Backend Tests (Python/Pytest)

### Setup

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=landing --cov=shared --cov=calorie_tracker --cov=fasting_tracker --cov=workout_tracker --cov=meal_planner

# Run specific tracker tests
pytest tests/test_habits_api.py
pytest tests/test_calorie_tracker_api.py
pytest tests/test_fasting_tracker_api.py
pytest tests/test_workout_tracker_api.py
pytest tests/test_meal_planner_api.py

# Run by marker
pytest -m calorie     # Only calorie tracker tests
pytest -m fasting     # Only fasting tracker tests
pytest -m workout     # Only workout tracker tests
pytest -m meal        # Only meal planner tests

# Run specific test class
pytest tests/test_habits_api.py::TestHabitToggle

# Run specific test
pytest tests/test_habits_api.py::TestHabitToggle::test_toggle_habit_creates_log
```

### Test Structure

#### `test_habits_api.py` (5 classes, 14 tests)

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

#### `test_calorie_tracker_api.py` (6 classes, 20+ tests)

**TestFoodSearch**
- `test_search_returns_results` - Food search returns matching items
- `test_food_item_to_dict` - Food item serialization

**TestFoodLogging**
- `test_create_food_log` - Create food log entries
- `test_update_serving_size` - Update servings and recalculate nutrition
- `test_food_log_to_dict` - Food log serialization

**TestDailyNutritionTotals**
- `test_get_daily_totals` - Calculate daily nutrition totals
- `test_meal_type_grouping` - Group logs by meal type

**TestUserNutritionGoals**
- `test_user_default_goals` - Verify default nutrition goals
- `test_user_goal_calculations` - Calculate goal grams from percentages
- `test_update_user_goals` - Update user goals

**TestFoodEditing**
- `test_edit_servings_updates_nutrition` - Update servings recalculates nutrition
- `test_delete_food_log` - Delete food log entries

#### `test_fasting_tracker_api.py` (6 classes, 25+ tests)

**TestFastCreation**
- `test_create_fast` - Create new fast
- `test_fast_with_note` - Create fast with note
- `test_user_default_fast_duration` - Verify default fast duration

**TestFastProgress**
- `test_fast_duration_calculation` - Calculate elapsed time
- `test_fast_progress_percentage` - Calculate progress %
- `test_fast_target_seconds` - Target seconds calculation
- `test_fast_progress_capped_at_100` - Progress doesn't exceed 100%
- `test_fast_remaining_seconds_when_active` - Remaining time calculation

**TestFastCompletion**
- `test_complete_fast` - Mark fast as completed
- `test_fast_is_not_active_after_end` - Verify completed fast is inactive
- `test_end_fast_early` - End fast before target time

**TestFastSerialization**
- `test_fast_to_dict` - Active fast serialization
- `test_completed_fast_to_dict` - Completed fast serialization

**TestFastQueries**
- `test_get_active_fasts` - Query active fasts
- `test_get_fast_history` - Query fast history

**TestFastDifferentDurations**
- `test_12_hour_fast` - 12 hour fasts
- `test_24_hour_fast` - 24 hour fasts
- `test_custom_duration_fast` - Custom duration fasts

#### `test_workout_tracker_api.py` (7 classes, 30+ tests)

**TestExerciseManagement**
- `test_create_strength_exercise` - Create strength exercise
- `test_create_cardio_exercise` - Create cardio exercise
- `test_exercise_to_dict` - Exercise serialization
- `test_user_exercises_query` - Query user exercises

**TestWorkoutCreation**
- `test_create_workout` - Create workout
- `test_add_exercise_to_workout` - Add exercises to workout
- `test_workout_exercise_to_dict` - Workout exercise serialization
- `test_workout_to_dict_with_exercises` - Workout with exercises
- `test_multiple_exercises_in_workout` - Multiple exercises per workout

**TestProgramManagement**
- `test_create_program` - Create training program
- `test_add_workouts_to_program` - Add workouts to program
- `test_program_to_dict_with_workouts` - Program serialization
- `test_program_workout_order` - Verify workout ordering

**TestWorkoutLogging**
- `test_create_workout_log` - Log a workout
- `test_custom_workout_log` - Custom workout logging
- `test_workout_log_with_program` - Log with program reference
- `test_complete_workout` - Mark workout as completed

**TestSetLogging**
- `test_log_set` - Log individual set
- `test_log_multiple_sets` - Multiple sets per workout
- `test_cardio_set_logging` - Cardio set logging
- `test_set_log_to_dict` - Set log serialization

**TestWorkoutProgress**
- `test_progressive_weight_increase` - Track weight progression
- `test_rep_progression` - Track rep increases

#### `test_meal_planner_api.py` (7 classes, 25+ tests)

**TestHouseholdManagement**
- `test_create_household` - Create household
- `test_household_has_creator` - Household creator relationship
- `test_multiple_households` - Multiple households per user

**TestMealCreation**
- `test_create_meal` - Create meal/recipe
- `test_meal_with_instructions` - Meal with instructions
- `test_meal_with_source_url` - Import from source URL
- `test_household_meals_query` - Query household meals

**TestMealFavorites**
- `test_favorite_meal` - Favorite a meal
- `test_unfavorite_meal` - Remove from favorites
- `test_is_favorite_by_user` - Check meal is favorited

**TestMealPlanning**
- `test_create_meal_plan_entry` - Create meal plan entry
- `test_custom_meal_plan_entry` - Custom meal plan
- `test_get_household_meal_plan_for_week` - Weekly meal plan query
- `test_meal_type_filtering` - Filter by meal type

**TestShoppingList**
- `test_create_shopping_list` - Create shopping list
- `test_add_item_to_shopping_list` - Add items
- `test_check_off_shopping_item` - Mark items as purchased
- `test_shopping_list_items_from_meal` - Items from meal

**TestHouseholdInvites**
- `test_create_invite` - Create household invite
- `test_invite_validity_check` - Verify invite validity
- `test_expired_invite` - Check expired invites
- `test_accept_invite` - Accept invite

**TestApiKeys**
- `test_generate_api_key` - Generate API key
- `test_create_api_key` - Create API key for user
- `test_deactivate_api_key` - Deactivate API key

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

## Test Summary

**Total Backend Tests**: 114+ tests covering:
- Habits Tracker: 14 tests
- Calorie Tracker: 20+ tests
- Fasting Tracker: 25+ tests
- Workout Tracker: 30+ tests
- Meal Planner: 25+ tests

**Total Frontend Tests**: 20+ tests covering:
- Date navigation
- Progress tracking
- Ring rendering
- API interactions
- Error handling

## Coverage Goals

- **Backend**: Aim for >80% coverage on API endpoints and core logic
- **Frontend**: Aim for >70% coverage on user interactions and calculations

Current coverage areas:
- ✅ Model creation and relationships
- ✅ Database queries and filtering
- ✅ Calculations and progress tracking
- ✅ Data serialization (to_dict)
- ✅ User interactions and state management
- ✅ API requests and error handling
- ✅ Date and timezone handling

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
