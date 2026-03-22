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
