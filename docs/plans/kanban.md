# Micro Fasting — Implementation Kanban

## Dependency Graph

```
Wave 1 (parallel): T1, T2, T5, T6
Wave 2 (after T1): T3
Wave 3 (after T3): T4, T7
```

---

## Todo

_(empty)_

---

## In Progress

_(empty)_

---

## Done

### T1 — MicroFast model ✓
Added `MicroFast` class to `fasting_tracker/models.py` with `is_active`, `duration_seconds`, `target_seconds`, `progress_pct` properties and `to_dict()`.

### T2 — Database migration ✓
- Added `default_micro_fast_minutes` column to `User` model in `shared/user.py`
- Created `migrations/versions/a1b2c3d4e5f6_add_micro_fast.py` (down_revision: `5ee16f998d22`)
- Updated `User.to_dict()` to include `default_micro_fast_minutes`
- Added `micro_fasts` relationship to `User`

### T3 — Micro fast API routes ✓
Added 7 routes to `fasting_tracker/api.py`:
- `POST /api/micro/start`
- `POST /api/micro/stop`
- `GET /api/micro/active`
- `GET /api/micro/today`
- `PATCH /api/micro/<id>`
- `DELETE /api/micro/<id>`
- `PUT /api/user/micro-goal`

### T4 — Micro fast dashboard UI ✓
- `fasting_tracker/main.py`: passes `default_micro_fast_minutes` to template
- `fasting_tracker/templates/dashboard.html`: full micro fast section (active state, idle form, today log)
- `fasting_tracker/static/js/micro_fast.js`: IIFE with start/stop, 5s polling, today log render

### T5 — Habit type + completion check ✓
- `landing/models.py`: updated comment to include `microfasting`
- `landing/completion.py`: added `microfasting` elif block querying `MicroFast` by `completed=True` and `ended_at` date

### T6 — Habit form UI ✓
- `landing/templates/habit_form.html`: added `<option value="microfasting">` to habit type select

### T7 — API tests ✓
Added `TestMicroFastAPI` to `tests/test_fasting_tracker_api.py` — 10 tests, all passing.
