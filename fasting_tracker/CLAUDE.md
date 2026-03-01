# Fasting Tracker

## Purpose & URL Prefix
Intermittent fasting timer with streak tracking and completion history.
**URL prefix:** `/fasting/`

## Key Files
- `__init__.py` — app factory (`create_app()`)
- `main.py` — dashboard, fast history views (main_bp)
- `api.py` — JSON API endpoints for start/stop/status (api_bp)
- `models.py` — Fast model
- `services/stats.py` — stateless stats computation
- `forms.py` — WTForms (settings/goal duration)
- `config.py` — app config

## Models (`fasting_tracker/models.py`)
| Model | Table | Key Columns |
|-------|-------|-------------|
| Fast | fast | user_id, started_at, ended_at, completed, target_hours, notes |

**Only one active fast at a time per user.** An "active" fast is one where `ended_at IS NULL`. Before starting a new fast, always check for and surface any existing active fast.

## User Setting (on shared User model)
`user.default_fast_hours` — default fasting duration goal (e.g., 16 for 16:8). Lives in `shared/user.py` — do not add it here.

## Timezone-Aware Time Math
All time calculations must be timezone-aware:
- Use `ZoneInfo(user.timezone or 'America/New_York')` for the user's local timezone
- `started_at` and `ended_at` are stored as UTC in the DB
- Convert to local time when computing elapsed duration, displaying "started at", etc.
- Use `datetime.now(timezone.utc)` for current time; convert with `.astimezone(user_tz)` for display

## Stats (`services/stats.py`)
Stateless functions called per request:
- `get_current_fast(user_id)` — returns active Fast or None
- `get_fast_history(user_id, limit)` — recent completed fasts
- `get_streak(user_id)` — current consecutive days with a completed fast
- `get_longest_fast(user_id)` — duration of longest completed fast

## Completion Logic
A day counts as "fasting goal met" when:
- A `Fast` record exists for the user
- `Fast.completed == True`
- `date(Fast.ended_at)` (in user's timezone) `== the target date`

This is consumed by `landing/completion.py` for the habit dashboard — do not change the Fast schema without updating the completion query.

## Routes (representative)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/fasting/` | Dashboard (current fast status + history) |
| POST | `/fasting/api/start` | Start a new fast |
| POST | `/fasting/api/stop` | End the active fast (marks completed=True if goal met) |
| DELETE | `/fasting/api/fast/<id>` | Delete a fast record |
| GET | `/fasting/api/status` | Current fast status JSON |
| GET | `/fasting/api/history` | Fast history JSON |

## Frontend
- **Templates:** `fasting_tracker/templates/fasting_tracker/`
- **JS:** `fasting_tracker/static/js/` — live timer (updates elapsed time), start/stop controls
- **CSS:** `fasting_tracker/static/css/`

## Constraints & Gotchas
- The live timer in the frontend polls `/fasting/api/status` periodically — keep this endpoint lightweight
- `completed` is set to `True` when the user stops a fast that met or exceeded `target_hours`; it stays `False` if they stop early
- Do not auto-complete fasts server-side — completion is always user-initiated via the stop action
- Past fasts can have notes added after the fact

## Shared Code Rules
- `shared/user.py` — DO NOT modify without coordinating with all sub-apps; adding columns requires a manual migration
- `shared/__init__.py` — `db = SQLAlchemy()` instance; import via `from shared import db`
- **DB:** `habitz/habitz/instance/habitz.db` — single SQLite file shared by all sub-apps
- **Auth:** session cookie `habitz_session` at path `/` — login at `/` works across all sub-apps
