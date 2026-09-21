# Habitz

A unified wellness platform running as a single web app.

| Path | App | Description |
|------|-----|-------------|
| `/` | Landing | Daily habit dashboard |
| `/meals/` | Meal Planner | Recipes, weekly planning, shopping lists |
| `/calories/` | Calorie Tracker | Daily calories and macros |
| `/fasting/` | Fasting Tracker | Intermittent fasting timers and goals |
| `/workouts/` | Workout Tracker | Programs, exercise logging, progress |
| `/budget/` | Budget Tracker | Weekly spending progress from Google Sheets |

A single gunicorn process serves all apps via Werkzeug's `DispatcherMiddleware` with a shared SQLite database and session cookie.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set SECRET_KEY at minimum
```

## Run

**Development:**
```bash
python run.py        # http://localhost:5001
```

**Production (gunicorn):**
```bash
gunicorn -w 4 -b 0.0.0.0:5001 wsgi:application
```

## Database

All apps share a single SQLite DB at `instance/habitz.db`, created automatically on first run. The landing app uses Flask-Migrate for schema changes; other apps use `db.create_all()`.

## Migrations

Run from `habitz/habitz/` with `FLASK_APP=landing`:

```bash
flask db migrate -m "description"
flask db upgrade
```

The deploy script runs `flask db upgrade` automatically.

## Environment variables

See `.env.example` for the full list. Required:

| Variable | Used by |
|----------|---------|
| `SECRET_KEY` | All apps (session signing) |
| `ANTHROPIC_API_KEY` | Meal Planner (recipe import) |
| `USDA_API_KEY` | Calorie Tracker (food search) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Budget Tracker (path to service account key file) |
| `GOOGLE_SHEET_ID` | Budget Tracker (spreadsheet ID from the budgetz sheet) |

## Apple Health Export

The workout tracker exposes `GET /workouts/api/export/apple-health` for syncing completed workouts to Apple Health via an iOS Shortcut.

**1. Generate an auth token** (re-running invalidates the old token):

```bash
python scripts/generate_health_token.py you@example.com
```

**2. Build the iOS Shortcut** (~10 steps):

1. **Get Contents of URL** — `https://<host>/workouts/api/export/apple-health?since=<cursor>` with header `Authorization: Bearer <token>`
2. Immediately **Save File** the response's `now` value as your cursor (`last-sync.txt`, iCloud Drive). *Save before logging — if the run crashes mid-loop, you lose workouts rather than duplicate them.*
3. **Repeat with Each** item in `workouts`:
   - **Log Workout** — activity type from `hk_type` (`traditional_strength_training`, `functional_strength_training`), start date `start`, end date `end`, duration `duration_minutes`
   - Energy: only pass `calories` **when not null** (passing 0 writes a bogus sample). Habitz doesn't capture calories for strength workouts yet, so energy is normally omitted.
4. On first run, set `<cursor>` empty or `1970-01-01` (defaults to the last 30 days)

The server is stateless: `since` (ISO date, optional) filters by `started_at`; the Shortcut owns the cursor. Only completed workouts are returned, oldest first. **Peloton-imported workouts are excluded** — the Peloton app syncs rides to Apple Health natively, and this export must not duplicate them. Sets/reps/weights are not exported (Shortcuts' Log Workout accepts type, dates, distance and energy only).

## Project structure

```
habitz/
├── wsgi.py                 # WSGI entry point (DispatcherMiddleware)
├── run.py                  # Dev server
├── requirements.txt
├── .env.example
├── landing/                # Daily habit dashboard
├── meal_planner/           # Meal planner app
├── calorie_tracker/        # Calorie tracker app
├── fasting_tracker/        # Fasting tracker app
├── workout_tracker/        # Workout tracker app
├── budget_tracker/         # Budget tracker (reads from Google Sheets)
└── scripts/prod/deploy.sh  # Production deploy script
```
