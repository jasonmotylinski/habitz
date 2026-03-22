# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Habitz platform.

## Platform Overview

Habitz is a unified wellness platform. The primary entry point is `habitz/habitz/` — a single-process WSGI app that mounts all sub-apps under one domain. The four original standalone apps in the repo root subdirectories (`meal-planner/`, `workout-tracker/`, etc.) are **not used in production**; the unified app is the live system.

## Unified App: `habitz/habitz/`

**Entry point:** `habitz/habitz/run.py` (dev, port 5000) / `habitz/habitz/wsgi.py` (production gunicorn)

**URL map (via `werkzeug.middleware.dispatcher.DispatcherMiddleware`):**
- `/` → landing / habit dashboard (`landing/`)
- `/meals/` → meal planner (`meal_planner/`)
- `/calories/` → calorie tracker (`calorie_tracker/`)
- `/fasting/` → fasting tracker (`fasting_tracker/`)
- `/workouts/` → workout tracker (`workout_tracker/`)

**Database:** Single SQLite DB at `habitz/habitz/instance/habitz.db` shared by all sub-apps.

**Auth:** Shared session cookie `habitz_session` at path `/` — login once at `/login`, works in all sub-apps. `SECRET_KEY` from `.env`.

**Shared code:**
- `shared/__init__.py` — `db = SQLAlchemy()` instance
- `shared/user.py` — unified `User` model (`__tablename__ = "user"`) with all columns from all sub-apps

## Package Structure

Each sub-app under `habitz/habitz/` is a renamed copy of the original `app/` package:

| URL prefix | Package | `create_app()` |
|------------|---------|----------------|
| `/` | `landing/` | `landing.create_app()` |
| `/meals/` | `meal_planner/` | `meal_planner.create_app(env)` |
| `/calories/` | `calorie_tracker/` | `calorie_tracker.create_app(env)` |
| `/fasting/` | `fasting_tracker/` | `fasting_tracker.create_app(env)` |
| `/workouts/` | `workout_tracker/` | `workout_tracker.create_app(env)` |

## Landing App (`landing/`)

The landing page is a **daily habit dashboard** — the primary daily interaction hub.

### Blueprints
- `auth_bp` (`landing/auth.py`) — login, register, logout at `/login`, `/register`, `/logout`
- `habits_bp` (`landing/habits.py`) — habit CRUD + daily index
- `api_bp` (`landing/api.py`) — JSON API endpoints

### Routes
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Daily habit dashboard (supports `?date=YYYY-MM-DD`) |
| GET | `/history` | Calendar history page |
| GET/POST | `/habits/new` | Create habit |
| GET/POST | `/habits/<id>/edit` | Edit habit |
| POST | `/habits/<id>/delete` | Archive or delete habit |
| POST | `/api/habits/<id>/toggle` | Toggle manual habit (JSON, supports `?date=`) |
| GET | `/api/habits/weekly` | Last 7 days ring data (JSON) |
| GET | `/api/habits/calendar` | Monthly calendar data (JSON, `?month=YYYY-MM`) |
| GET/POST | `/api/daily/note` | Daily note for a date |
| GET/POST | `/api/daily/mood` | Daily mood (1–5 scale) for a date |
| GET | `/api/daily/summary` | Habits + note + mood for a date |

### Models (`landing/models.py`)
- `Habit` — user-defined habits (`manual` | `workout` | `calories` | `fasting` | `meals`)
- `HabitLog` — completion records for all habit types (unified source of truth for streaks)
- `DailyNote` — free-text daily journal entry per user per date
- `DailyMood` — mood score (1–5) + optional notes per user per date

### Completion logic (`landing/completion.py`)
- **manual** → `HabitLog` row exists for that date
- **workout** → `WorkoutLog` with `completed_at IS NOT NULL` and `date(completed_at) == today`
- **calories** → sum of `FoodLog.calories` for today ≥ `user.daily_calorie_goal`
- **fasting** → `Fast` with `completed=True` and `date(ended_at) == today`
- **meals** → `MealPlan` row exists for today in user's household

App-linked habits are synced into `HabitLog` on each page load (written if done, removed if not). This keeps streak calculation uniform.

### Schema migrations
The landing app uses **Flask-Migrate** (Alembic). Migrations live in `habitz/habitz/migrations/versions/`. After modifying any model, run:
```bash
flask db migrate -m "description"   # generate
flask db upgrade                     # apply
```
The deployment script runs `flask db upgrade` automatically. Because the landing app doesn't import all sub-app models, **use `op.batch_alter_table` in manual migrations** rather than autogenerate (avoids FK resolution errors from unloaded models like `household`).

## Shared User Model (`shared/user.py`)

Key columns on `User`:
- `email`, `username`, `password_hash`
- `household_id` (meal planner)
- `daily_calorie_goal`, `protein_goal_pct`, `carb_goal_pct`, `fat_goal_pct` (calorie tracker)
- `default_fast_hours` (fasting tracker)
- `timezone` — IANA timezone string, default `'America/New_York'`

**Note:** The `timezone` column was added after initial deployment. Run `python scripts/add_timezone_column.py` on any existing database that pre-dates this column.

## Meal Planner Auth (`meal_planner/auth.py`)

The meal planner has its own `auth_bp` with `/login`, `/register`, `/logout` routes — usable standalone without the landing page login. It uses the same `habitz.db` user table.

## Utility Scripts (`habitz/habitz/scripts/`)

| Script | Purpose |
|--------|---------|
| `reset_password.py` | Reset a user's password by email (case-insensitive lookup) |
| `add_timezone_column.py` | One-time migration: adds `timezone` column to `user` table |
| `migrate_to_habitz_db.py` | Original migration from 4 separate DBs to unified `habitz.db` |

## Bug Fixes

When a bug is reported and fixed, always add a regression test to the corresponding test file in `habitz/habitz/tests/`. The test must:
- Reproduce the failure mode (e.g. assert the wrong behavior raises an error, or assert the correct output)
- Pass against the fixed code
- Be added to the relevant `Test*` class in `tests/test_<sub_app>_api.py`

Run tests with: `venv/bin/python -m pytest tests/test_workout_tracker_api.py -v` (swap filename for the relevant sub-app).

## Budget Tracker (`budget_tracker/`)

**URL prefix:** `/budget/`

**Required env vars** (add to `habitz/habitz/.env`):
- `GOOGLE_SERVICE_ACCOUNT_JSON` — absolute path to the Google service account key file (copy from budgetz)
- `GOOGLE_SHEET_ID` — spreadsheet ID from the budgetz Google Sheet URL

The service account JSON file is at `/Users/jason/code/personal/habitz/budget-490711-92178b410d52.json`.

## Shared Conventions

- **Framework**: Flask with application factory pattern (`create_app()`)
- **Database**: SQLite + SQLAlchemy ORM; `db.create_all()` for new tables; manual `ALTER TABLE` for new columns on existing tables
- **Auth**: Flask-Login; `werkzeug.security` for password hashing
- **Frontend**: Server-rendered Jinja2 + vanilla JS (IIFEs) + custom CSS; no frontend framework
- **Config**: `.env` file for secrets; `DATABASE_URL` env var overrides `.env` loading
- **Timezone**: All user-facing date logic uses `ZoneInfo(user.timezone or 'America/New_York')`

## Key Design Decisions

- Each sub-app runs its own Flask instance but shares `habitz.db` via a common `DATABASE_URL` env var pointing to the same file.
- `url_for()` in Jinja2 templates correctly generates sub-app-relative URLs when served through `DispatcherMiddleware` (SCRIPT_NAME is set automatically).
- Workout tracker JS uses `window.SCRIPT_ROOT` (injected in `base.html`) to prefix API paths correctly.
- The unified session cookie means a user logged in at `/` is also logged in at `/meals/`, `/workouts/`, etc.
- New tables (e.g., `habit`, `habit_log`, `daily_note`, `daily_mood`) are auto-created by `db.create_all()` in `landing/__init__.py`.
