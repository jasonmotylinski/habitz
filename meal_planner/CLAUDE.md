# Meal Planner

## Purpose & URL Prefix
Household-based weekly meal planning with shopping list generation and recipe import.
**URL prefix:** `/meals/`

## Key Files
- `__init__.py` — app factory (`create_app()`)
- `auth.py` — login/register/logout (auth_bp); usable standalone without landing auth
- `main.py` — dashboard, household overview (main_bp)
- `meals.py` — meal CRUD (meals_bp)
- `planner.py` — weekly planner view + meal assignment (planner_bp)
- `shopping.py` — shopping list view + item toggle (shopping_bp)
- `household.py` — household creation, invites, member management (household_bp)
- `api.py` — JSON API endpoints (api_bp)
- `api_keys.py` — API key management (api_keys_bp)
- `settings.py` — user/household settings (settings_bp)
- `models.py` — all meal planner models
- `recipe_importer.py` — async recipe import logic
- `jobs/process_pending_recipes.py` — cron job to process pending recipe imports
- `forms.py` — WTForms for meals, households, settings
- `utils.py` — helpers (e.g., shopping list generation)

## Models (`meal_planner/models.py`)
| Model | Table | Key Columns |
|-------|-------|-------------|
| Household | household | id, name, created_by |
| HouseholdInvite | household_invite | household_id, email, token, accepted |
| ApiKey | api_key | user_id, key, name, created_at |
| Meal | meal | household_id, name, description, recipe_url, import_status |
| meal_favorites | meal_favorites | user_id, meal_id (association table) |
| MealPlan | meal_plan | household_id, meal_id, date, slot (breakfast/lunch/dinner/snack) |
| ShoppingList | shopping_list | household_id, week_start, generated_at |
| ShoppingListItem | shopping_list_item | list_id, ingredient, quantity, unit, checked |

**All queries must be scoped to `household_id`** — users belong to a household and only see that household's data.

## Async Recipe Import
- `Meal.import_status` values: `pending` | `imported` | `failed`
- New meals with a `recipe_url` start as `pending`
- `jobs/process_pending_recipes.py` is a cron job that picks up pending meals, scrapes the URL via `recipe_importer.py`, and updates the meal record
- Do not block on recipe import in request handlers

## Routes (representative)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/meals/` | Dashboard |
| GET/POST | `/meals/meals/new` | Create meal |
| GET/POST | `/meals/meals/<id>/edit` | Edit meal |
| GET | `/meals/planner` | Weekly planner view |
| POST | `/meals/planner/assign` | Assign meal to day/slot |
| GET | `/meals/shopping` | Shopping list |
| POST | `/meals/shopping/toggle/<item_id>` | Toggle item checked |
| GET/POST | `/meals/household` | Household management |
| GET/POST | `/meals/login` | Auth (standalone) |
| GET/POST | `/meals/register` | Auth (standalone) |

## Frontend
- **Templates:** `meal_planner/templates/meal_planner/`
- **JS:**
  - `shopping.js` — AJAX toggle for shopping list items
  - `meal-form.js` — meal creation/editing form interactions
  - `onboarding.js` — household onboarding flow
- **CSS:** `meal_planner/static/css/`

## Constraints & Gotchas
- The meal planner has its own `auth_bp` with `/login`, `/register`, `/logout` — this is intentional for standalone use. It uses the same `habitz.db` user table.
- `user.household_id` on the shared User model links a user to their household. Check this before any household-scoped query.
- Shopping list generation can be slow — avoid calling it synchronously during page load if possible.
- Recipe import is async by design; do not add synchronous scraping to request handlers.

## Shared Code Rules
- `shared/user.py` — DO NOT modify without coordinating with all sub-apps; adding columns requires a manual migration
- `shared/__init__.py` — `db = SQLAlchemy()` instance; import via `from shared import db`
- **DB:** `habitz/habitz/instance/habitz.db` — single SQLite file shared by all sub-apps
- **Auth:** session cookie `habitz_session` at path `/` — login at `/` works across all sub-apps
