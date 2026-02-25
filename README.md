# Habitz

A unified wellness platform running four trackers as a single web app.

| Path | App | Description |
|------|-----|-------------|
| `/` | Landing | App hub |
| `/meals/` | Meal Planner | Recipes, weekly planning, shopping lists |
| `/calories/` | Calorie Tracker | Daily calories and macros |
| `/fasting/` | Fasting Tracker | Intermittent fasting timers and goals |
| `/workouts/` | Workout Tracker | Programs, exercise logging, progress |

Each tracker has its own SQLite database and independent auth. A single gunicorn process serves all four via Werkzeug's `DispatcherMiddleware`.

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

## Databases

Each app stores its SQLite DB in its own `instance/` directory. They are created automatically on first run.

| App | Database path |
|-----|--------------|
| Meal Planner | `instance/meal_planner.db` |
| Calorie Tracker | `calorie_tracker/instance/calorie_tracker.db` |
| Fasting Tracker | `fasting_tracker/instance/fasting_tracker.db` |
| Workout Tracker | `workout_tracker/instance/workout.db` |

## Migrations

Each sub-app manages its own schema with Flask-Migrate. To run migrations for a specific app, `cd` into its source directory and use the standard Flask-Migrate commands, or point `FLASK_APP` at a wrapper that creates just that sub-app. For most deploys, `db.create_all()` (called automatically on startup) is sufficient.

## Environment variables

See `.env.example` for the full list. Required:

| Variable | Used by |
|----------|---------|
| `SECRET_KEY` | All apps (session signing) |
| `ANTHROPIC_API_KEY` | Meal Planner (recipe import) |
| `USDA_API_KEY` | Calorie Tracker (food search) |

## Project structure

```
habitz/
├── wsgi.py                 # WSGI entry point (DispatcherMiddleware)
├── run.py                  # Dev server
├── requirements.txt
├── .env.example
├── landing/                # Landing page
├── meal_planner/           # Meal planner app
├── calorie_tracker/        # Calorie tracker app
├── fasting_tracker/        # Fasting tracker app
├── workout_tracker/        # Workout tracker app
└── scripts/prod/deploy.sh  # Production deploy script
```
