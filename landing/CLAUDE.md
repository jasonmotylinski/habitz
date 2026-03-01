# Landing App (Habit Dashboard)

## Purpose & URL Prefix
Daily habit dashboard — the primary daily interaction hub.
**URL prefix:** `/` (root)

## Key Files
- `__init__.py` — app factory (`create_app()`); calls `db.create_all()` for landing models
- `auth.py` — login, register, logout routes (auth_bp)
- `habits.py` — habit CRUD + daily dashboard (habits_bp)
- `api.py` — JSON API endpoints (api_bp)
- `models.py` — Habit, HabitLog, DailyNote, DailyMood
- `completion.py` — cross-app completion logic; do NOT duplicate elsewhere
- `forms.py` — WTForms for habit creation/editing

## Models (`landing/models.py`)
| Model | Table | Key Columns |
|-------|-------|-------------|
| Habit | habit | user_id, name, type (manual/workout/calories/fasting/meals), is_archived, created_at |
| HabitLog | habit_log | habit_id, user_id, date, completed |
| DailyNote | daily_note | user_id, date, content |
| DailyMood | daily_mood | user_id, date, mood (1–5), notes |

## Routes
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Daily habit dashboard (`?date=YYYY-MM-DD`) |
| GET | `/history` | Monthly calendar with completion rings |
| GET/POST | `/habits/new` | Create habit |
| GET/POST | `/habits/<id>/edit` | Edit habit |
| POST | `/habits/<id>/delete` | Archive or delete habit |
| POST | `/api/habits/<id>/toggle` | Toggle manual habit (JSON, `?date=`) |
| GET | `/api/habits/weekly` | Last 7 days ring data (JSON) |
| GET | `/api/habits/calendar` | Monthly calendar data (`?month=YYYY-MM`) |
| GET/POST | `/api/daily/note` | Daily note for a date |
| GET/POST | `/api/daily/mood` | Daily mood (1–5) for a date |
| GET | `/api/daily/summary` | Habits + note + mood for a date |
| GET/POST | `/login` | Auth |
| GET/POST | `/register` | Auth |
| POST | `/logout` | Auth |

## Completion Logic (`landing/completion.py`)
Cross-app queries that determine if a habit type is "done" for a date:
- **manual** → HabitLog row exists for that date
- **workout** → WorkoutLog with `completed_at IS NOT NULL` and `date(completed_at) == date`
- **calories** → `sum(FoodLog.calories)` for date `>= user.daily_calorie_goal`
- **fasting** → Fast with `completed=True` and `date(ended_at) == date`
- **meals** → MealPlan row exists for date in user's household

App-linked habits are synced into HabitLog on each page load. **Do not replicate this logic** — always import from `completion.py`.

## Frontend
- **Templates:** `landing/templates/landing/` — `index.html`, `history.html`, `habit_form.html`
- **JS:** `landing/static/js/habits.js` — dashboard ring interactions, toggle calls, calendar
- **CSS:** `landing/static/css/`

## Migrations
This app uses **Flask-Migrate** (Alembic). Migrations are in `habitz/habitz/migrations/versions/`.
- Generate: `flask db migrate -m "description"`
- Apply: `flask db upgrade`
- **NEVER use autogenerate** — fails because User has FK to `household` from meal_planner which isn't loaded in landing app context
- **Always use `op.batch_alter_table`** in manually written migrations (SQLite requires it for column changes)
- Deployment script runs `flask db upgrade` automatically

## Shared Code Rules
- `shared/user.py` — DO NOT modify without coordinating with all sub-apps; adding columns requires a manual migration + running `scripts/add_timezone_column.py` pattern on existing DBs
- `shared/__init__.py` — `db = SQLAlchemy()` instance; import via `from shared import db`
- **DB:** `habitz/habitz/instance/habitz.db` — single SQLite file shared by all sub-apps
- **Auth:** session cookie `habitz_session` at path `/` — login at `/` works across all sub-apps; `flask_login.current_user` is available in all blueprints
