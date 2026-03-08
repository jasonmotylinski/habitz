# Micro Fasting: Research & Integration Plan

## What Is Micro Fasting?

Micro fasting is the practice of maintaining intentional gaps between meals — typically 3–6 hours — without snacking. Unlike intermittent fasting (which is about a single daily eating window, usually 12–24+ hours), micro fasting treats each between-meal window as its own timed challenge.

The primary target use case: start a timer after lunch, hit a 3–4 hour gap before dinner, feel rewarded for not snacking.

### Science

The physiological basis is real, even if "micro fasting" isn't a widely-used clinical term:

- **Migrating Motor Complex (MMC):** The gut only activates this cleansing wave pattern during fasting states. It cycles every 90–120 minutes when no food is present, clearing residual nutrients and bacteria from the small intestine. Snacking between meals interrupts it. A 3+ hour gap allows 1–2 full MMC cycles.
- **Insulin normalization:** Each meal triggers an insulin spike. Consistent 3–5 hour gaps between meals let insulin return to baseline, improving insulin sensitivity over time. Chronic snacking keeps insulin chronically elevated.
- **Appetite reset:** Ghrelin (hunger hormone) follows ultradian rhythms tied to meal timing. Honoring meal gaps trains the hunger cycle rather than confusing it with constant eating.

Sources: [PMC: Meal Frequency and Timing](https://pmc.ncbi.nlm.nih.gov/articles/PMC6520689/), [Jefferson Health: IF and Insulin Resistance](https://www.jeffersonhealth.org/your-health/living-well/intermittent-fasting-and-insulin-resistance-benefits-beyond-weight-loss), [Gut Microbiota for Health: Eating Rhythmicity](https://www.gutmicrobiotaforhealth.com/intermittent-fasting-and-eating-rhythmicity-what-we-know-about-their-impact-on-metabolic-and-gut-health/)

### Existing Apps

No mainstream app focuses specifically on between-meal fasting windows. The big IF trackers (Zero, DoFasting, MyFitnessPal IF tracker) are all built around the single-daily-window model — start fasting after dinner, break it with breakfast. They conflate "fasting" with "overnight abstention from food."

The gap in the market: a micro fast timer that treats lunch→dinner as its own completion event, with streak tracking and habit integration.

---

## Why the Existing Fasting Tracker Doesn't Fit

The existing `Fast` model (`fasting_tracker/`) has two hard constraints that don't match micro fasting:

1. **One active fast per user at a time.** Enforced at the API level. Micro fasts between multiple meal pairs in a day (breakfast-lunch AND lunch-dinner) would conflict.
2. **`target_hours` is an integer.** Micro fasts are measured in minutes (e.g., 3.5 hours = 210 minutes). Storing `target_hours = 3` loses resolution; storing `target_hours = 0` breaks completion logic.

The UI is also oriented around long-duration endurance ("16 hours remaining") rather than the short, deliberate meal-gap context.

Extending the existing model with a `fast_type` discriminator would work technically but would tangle two meaningfully different behaviors into one screen and one set of API constraints.

---

## Proposed Architecture

### 1. New Model: `MicroFast`

Add to `fasting_tracker/models.py`:

```python
class MicroFast(db.Model):
    __tablename__ = 'micro_fast'

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    started_at     = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ended_at       = db.Column(db.DateTime, nullable=True)
    target_minutes = db.Column(db.Integer, nullable=False, default=180)  # 3 hours default
    completed      = db.Column(db.Boolean, default=False)
    label          = db.Column(db.String(50), nullable=True)  # e.g. 'lunch-dinner'
    note           = db.Column(db.String(200), nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
```

Key differences from `Fast`:
- `target_minutes` (not `target_hours`) — supports 30-minute resolution
- `label` — contextual name for the window (breakfast-lunch, lunch-dinner, dinner-bedtime, custom)
- Multiple per day allowed — no one-active-at-a-time database constraint, though the UI enforces one active micro fast at a time (simpler UX)

### 2. New User Setting: `default_micro_fast_minutes`

Add to `shared/user.py`:

```python
default_micro_fast_minutes = db.Column(db.Integer, default=180)
```

Requires a manual Flask-Migrate migration (same pattern as other columns added post-deploy). Default 180 minutes = 3 hours.

### 3. New API Routes in `fasting_tracker/api.py`

```
POST   /fasting/api/micro/start    — start a micro fast (label, target_minutes optional)
POST   /fasting/api/micro/stop     — stop active micro fast; sets completed if >= target
GET    /fasting/api/micro/active   — active micro fast or null
GET    /fasting/api/micro/today    — all micro fasts for today (for dashboard)
PATCH  /fasting/api/micro/<id>     — edit a completed micro fast (note, times)
DELETE /fasting/api/micro/<id>     — delete a micro fast record
PUT    /fasting/api/user/micro-goal — update default_micro_fast_minutes
```

Logic mirrors the existing `Fast` API:
- `stop` sets `ended_at = now`, `completed = (duration_seconds / 60) >= target_minutes`
- Only one active micro fast at a time (API returns 400 if one exists on start)

### 4. UI: Micro Fast Panel in `/fasting/`

Add a collapsible "Micro Fast" section to the fasting tracker dashboard (`main.py` + template), below the main IF timer:

- **Active state:** Live timer counting up from `started_at`, target countdown ("1h 23m until goal"), progress ring
- **Idle state:** "Start Micro Fast" button; label dropdown (Breakfast → Lunch / Lunch → Dinner / Dinner → Bedtime / Custom); target duration selector (pre-filled from `default_micro_fast_minutes`)
- **Today's log:** Compact list of completed micro fasts for today (label, duration, check if goal was met)
- **Settings:** Link to set default target minutes

The live timer should use the same polling pattern as the existing fasting timer (`/fasting/api/micro/active`).

### 5. New Habit Type: `microfasting`

Add `'microfasting'` to the `habit_type` enum in `landing/models.py` (comment only — SQLite doesn't enforce enums):

```python
# 'manual' | 'workout' | 'calories' | 'fasting' | 'meals' | 'microfasting'
```

Add completion check in `landing/completion.py`:

```python
elif habit.habit_type == 'microfasting':
    from fasting_tracker.models import MicroFast
    return db.session.query(MicroFast).filter(
        MicroFast.user_id == user.id,
        MicroFast.completed == True,
        func.date(MicroFast.ended_at) == today,
    ).first() is not None
```

This means: the habit is satisfied if **any** micro fast completed successfully today. No label filtering — if you did your lunch→dinner gap, you win the day regardless of what it was called.

### 6. Habit Form: Creating a Micro Fasting Habit

In the habit creation form (`landing/forms.py` + `habit_form.html`), add `microfasting` as a selectable type alongside `fasting`. Description shown to user:

> "Tracks whether you completed a between-meal micro fast today. Start a timer after a meal from the Fasting tracker."

---

## Migration Plan

### Step 1: `micro_fast` table
```bash
# In habitz/habitz/ with FLASK_APP=landing set
flask db migrate -m "add micro_fast table"
flask db upgrade
```
Or write a manual migration using `op.create_table(...)` if autogenerate causes FK issues.

### Step 2: `default_micro_fast_minutes` column on `user`
Write a manual migration (do NOT autogenerate — same FK resolution issue as noted in CLAUDE.md):
```python
def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(
            sa.Column('default_micro_fast_minutes', sa.Integer(), nullable=True)
        )
```

---

## What This Does NOT Change

- The existing `Fast` model and IF tracker are untouched.
- The `fasting` habit type in the landing app continues to check `Fast.completed`.
- Users can run both — an IF fast overnight AND micro fasts between daytime meals are separate records.
- The one-active-IF-fast constraint remains in place.

---

## Open Questions

1. **Should micro fasts be limited to one active at a time?** The plan says yes (simpler). If the user wants to track breakfast-lunch and lunch-dinner independently with overlapping timers, this needs rethinking.

2. **Per-label habits?** Currently the habit completion is "any completed micro fast today." A future enhancement: a habit that only counts a specific label (e.g., must be the `lunch-dinner` window). This would require storing the label on the `Habit` model or adding a `required_label` column.

3. **Minimum useful target.** Should there be a floor on `target_minutes`? 30 minutes is technically a valid gap but not meaningful. The UI could suggest a minimum of 60 or 90 minutes and explain why.

4. **Streak display.** The `/fasting/` dashboard already shows IF streaks. A micro fast streak (consecutive days with at least one completed micro fast) would be a natural addition to the same page.
