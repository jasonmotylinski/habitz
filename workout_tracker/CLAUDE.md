# Workout Tracker

## Purpose & URL Prefix
Program-based workout tracking with exercises, sets, and completion logging.
**URL prefix:** `/workouts/`

## Key Files
- `__init__.py` — app factory (`create_app()`); injects `SCRIPT_ROOT` into Jinja context
- `views.py` — all template-rendering routes (single blueprint)
- `api/__init__.py` — registers API blueprints
- `api/exercises.py` — exercise CRUD API
- `api/logs.py` — workout log + set log API
- `api/programs.py` — program management API
- `api/workouts.py` — workout CRUD API
- `models/` — models split by domain (see below)
- `config.py` — app config

## Models (split across `workout_tracker/models/`)
| Model | File | Key Columns |
|-------|------|-------------|
| Program | models/program.py | user_id, name, description |
| ProgramWorkoutOrder | models/program.py | program_id, workout_id, order |
| Workout | models/workout.py | user_id, name, notes |
| WorkoutExercise | models/workout.py | workout_id, exercise_id, sets, reps, weight |
| Exercise | models/exercise.py | user_id, name, muscle_group, equipment |
| WorkoutLog | models/log.py | user_id, workout_id, started_at, completed_at |
| SetLog | models/log.py | workout_log_id, exercise_id, set_number, reps, weight |

**All queries must be scoped to `current_user.id`** — no shared household, each user has their own data.

## Architecture: API-First
- `views.py` renders templates; it does NOT contain data mutation logic
- All data operations (create, update, delete) go through the `api/` blueprints which return JSON
- Frontend JS calls the API endpoints and updates the DOM
- When adding new functionality: add an API endpoint first, then wire up the JS

## CRITICAL: SCRIPT_ROOT and API Calls
- `window.SCRIPT_ROOT` is injected in `base.html` (set to the app's SCRIPT_NAME from DispatcherMiddleware)
- **All JS API calls MUST use the `api.js` fetch wrapper** (`workout_tracker/static/js/api.js`)
- `api.js` prepends `window.SCRIPT_ROOT` to all API paths
- Never hardcode `/workouts/` in JS — always use relative paths through the `api.js` wrapper
- Example: `apiFetch('/api/logs/123/complete')` → resolves to `/workouts/api/logs/123/complete`

## Completion Logic
A workout counts as "completed today" when:
- `WorkoutLog` exists for the user
- `WorkoutLog.completed_at IS NOT NULL`
- `date(WorkoutLog.completed_at) == today` (in user's timezone)

This is consumed by `landing/completion.py` for the habit dashboard — do not change the schema without updating the completion query.

## Routes (representative)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/workouts/` | Dashboard / active program |
| GET | `/workouts/programs` | List programs |
| GET | `/workouts/programs/<id>` | Program detail |
| GET | `/workouts/log/<log_id>` | Active workout log |
| GET | `/workouts/history` | Workout history |
| POST | `/workouts/api/logs` | Start a new workout log |
| POST | `/workouts/api/logs/<id>/complete` | Mark workout complete |
| POST | `/workouts/api/logs/<id>/sets` | Log a set |

## Frontend
- **Templates:** `workout_tracker/templates/workout_tracker/`
- **JS:** `workout_tracker/static/js/api.js` — fetch wrapper (always use this)
- **CSS:** `workout_tracker/static/css/`

## Constraints & Gotchas
- Models are split into separate files under `models/` — import from the model file, not the package root, to avoid circular imports
- The `ProgramWorkoutOrder` join table controls workout order within a program; maintain `order` field integrity
- Set logs are immutable after creation — no edit endpoint by design
- `WorkoutLog.started_at` is always set; `completed_at` is null until the user explicitly finishes

## Shared Code Rules
- `shared/user.py` — DO NOT modify without coordinating with all sub-apps; adding columns requires a manual migration
- `shared/__init__.py` — `db = SQLAlchemy()` instance; import via `from shared import db`
- **DB:** `habitz/habitz/instance/habitz.db` — single SQLite file shared by all sub-apps
- **Auth:** session cookie `habitz_session` at path `/` — login at `/` works across all sub-apps
