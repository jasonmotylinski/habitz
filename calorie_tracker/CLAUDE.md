# Calorie Tracker

## Purpose & URL Prefix
Daily food logging with macro tracking against user-defined calorie and macro goals.
**URL prefix:** `/calories/`

## Key Files
- `__init__.py` — app factory (`create_app()`)
- `main.py` — daily dashboard, food log views (main_bp)
- `food.py` — food item CRUD, USDA/external food search (food_bp)
- `api.py` — JSON API endpoints (api_bp)
- `models.py` — FoodItem, UsdaFood, FoodLog
- `services/nutrition.py` — multi-source food search (USDA, Nutritionix, OpenFoodFacts)
- `services/stats.py` — on-the-fly stats computation (daily totals, macro breakdown)
- `forms.py` — WTForms for food logging
- `config.py` — app config (API keys for nutrition services)

## Models (`calorie_tracker/models.py`)
| Model | Table | Key Columns |
|-------|-------|-------------|
| FoodItem | food_item | user_id, name, calories, protein, carbs, fat, serving_size, serving_unit, source |
| UsdaFood | usda_food | fdc_id, name, calories, protein, carbs, fat (cached USDA data) |
| FoodLog | food_log | user_id, date, food_item_id, quantity, calories, protein, carbs, fat, meal_type |

## Macro Goals (on shared User model)
These columns live in `shared/user.py` — do not add duplicate columns here:
- `user.daily_calorie_goal` — target daily calories (int)
- `user.protein_goal_pct` — protein as % of calories
- `user.carb_goal_pct` — carbs as % of calories
- `user.fat_goal_pct` — fat as % of calories

## Food Search (`services/nutrition.py`)
Multi-source search with fallback priority:
1. User's own saved food items
2. USDA FoodData Central API
3. Nutritionix API
4. OpenFoodFacts API

Results are cached in `usda_food` table to avoid repeated API calls. API keys are configured via environment variables in `config.py`.

## Stats (`services/stats.py`)
Stateless functions called per request — no caching layer:
- `get_daily_totals(user_id, date)` — sum of calories/macros for a date
- `get_macro_breakdown(user_id, date)` — percentage breakdown vs goals
- `get_weekly_summary(user_id)` — 7-day aggregate

## Completion Logic
A day counts as "calories goal met" when:
- `sum(FoodLog.calories) for date >= user.daily_calorie_goal`

This is consumed by `landing/completion.py` for the habit dashboard — do not change the FoodLog schema without updating the completion query.

## Routes (representative)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/calories/` | Daily dashboard (`?date=YYYY-MM-DD`) |
| POST | `/calories/api/log` | Add food log entry |
| DELETE | `/calories/api/log/<id>` | Remove food log entry |
| GET | `/calories/api/search` | Search foods (multi-source) |
| GET/POST | `/calories/food/new` | Create custom food item |
| GET | `/calories/api/stats` | Daily stats JSON |

## Frontend
- **Templates:** `calorie_tracker/templates/calorie_tracker/`
- **JS:** `calorie_tracker/static/js/` — food search, log entry, macro ring chart
- **CSS:** `calorie_tracker/static/css/`

## Constraints & Gotchas
- `FoodLog` stores denormalized macro values (copied from FoodItem at log time) — editing a FoodItem does not retroactively change old logs
- `meal_type` on FoodLog: `breakfast` | `lunch` | `dinner` | `snack`
- USDA API calls can be slow — consider the caching layer before adding new external calls
- All date arithmetic uses `user.timezone` (via `ZoneInfo`) for correct "today" boundaries

## Shared Code Rules
- `shared/user.py` — DO NOT modify without coordinating with all sub-apps; adding columns requires a manual migration
- `shared/__init__.py` — `db = SQLAlchemy()` instance; import via `from shared import db`
- **DB:** `habitz/habitz/instance/habitz.db` — single SQLite file shared by all sub-apps
- **Auth:** session cookie `habitz_session` at path `/` — login at `/` works across all sub-apps
