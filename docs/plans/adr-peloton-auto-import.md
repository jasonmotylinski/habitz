# ADR: Automatic Peloton Workout Import

## Status

Proposed

## Context

Jason currently logs Peloton rides manually in the Habitz workout tracker. Each ride is recorded as a "Cardio" workout with two SetLog entries: a "Peloton - Main set" (duration in minutes) and a "Peloton - Cool down" (duration in minutes). This manual process is tedious and easy to forget, leading to incomplete workout history.

There is an existing local project at `/Users/jason/code/personal/peloton-planner/` that already integrates with the Peloton API. It handles authentication (JWT token via Playwright browser automation or Auth0 password grant) and uses Peloton's REST API for class data. However, it only builds workout stacks — it does not fetch or store workout performance data.

The Peloton API provides access to completed workout data via:
- `GET /api/user/{userId}/workouts` — paginated list of completed workouts
- `GET /api/workout/{workoutId}` — detailed workout metrics (output, calories, cadence, heart rate)
- Authentication via session cookie (`POST /api/auth/login`) or JWT Bearer token

### Existing Habitz Cardio Schema

Cardio workouts in Habitz use the same tables as strength, but with different field usage:

| Table | Cardio Usage |
|-------|--------------|
| `exercises` | `type='cardio'`, name like "Peloton - Main set" |
| `workout_logs` | `workout_id` references a Cardio template, `started_at`/`completed_at` set |
| `set_logs` | `duration_minutes` set, `actual_reps=NULL`, `weight=NULL`, `completed=True` |

Each Peloton ride creates 2 SetLog rows: one for the main ride, one for cool-down.

### Peloton API Authentication

The peloton-planner project demonstrates three authentication methods:
1. **JWT Bearer Token** (preferred) — stored in `.env`, expires ~48 hours
2. **Auth0 Password Grant** — uses username + password with Auth0 client ID
3. **Playwright Browser Automation** — headless Firefox captures JWT from browser traffic

For automated daily imports, we need credentials that don't expire daily. The Auth0 password grant or stored JWT with periodic refresh via Playwright are viable options.

---

## Decision

We will implement an automatic Peloton workout import feature that runs daily via cron, fetches recent completed rides from the Peloton API, and creates WorkoutLog + SetLog records in Habitz.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Cron Job (daily at 6:00 AM)                                │
│  workout_tracker/jobs/import_peloton_workouts.py            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  pylotoncycle Library                                       │
│  1. PylotonCycle(username, password)                        │
│  2. GetRecentWorkouts(10)                                   │
│  3. GetWorkoutMetricsById(workout_id) for each new ride     │
│  4. ParseMetricsData(metrics) for clean output              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Habitz Workout Tracker                                     │
│  1. Check dedup (peloton_workout_id not already imported)   │
│  2. Create WorkoutLog (workout_id=Cardio template)          │
│  3. Create SetLog for main ride (duration_minutes)          │
│  4. Create PelotonWorkout record with rich metrics          │
└─────────────────────────────────────────────────────────────┘
```

### 1. New Model: `PelotonWorkout` (dedup tracker)

Add to `workout_tracker/models/log.py`:

```python
class PelotonWorkout(db.Model):
    __tablename__ = 'peloton_workouts'

    id                  = db.Column(db.Integer, primary_key=True)
    user_id             = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    peloton_workout_id  = db.Column(db.String(64), unique=True, nullable=False)
    ride_title          = db.Column(db.String(200))
    ride_duration       = db.Column(db.Integer)  # minutes
    total_output        = db.Column(db.Float)    # kJ
    calories            = db.Column(db.Integer)
    average_cadence     = db.Column(db.Float)
    average_resistance   = db.Column(db.Float)
    average_heartrate   = db.Column(db.Float)
    leaderboard_rank    = db.Column(db.Integer)
    total_leaderboard   = db.Column(db.Integer)
    imported_at         = db.Column(db.DateTime, default=datetime.utcnow)
    workout_log_id      = db.Column(db.Integer, db.ForeignKey('workout_logs.id'), nullable=True)
```

This table serves two purposes:
- **Deduplication:** `peloton_workout_id` is unique — we skip rides already imported
- **Rich metadata:** Store Peloton-specific metrics that don't fit in SetLog (output, leaderboard rank, etc.)

### 2. Peloton Credentials

Store in `habitz/habitz/.env` (gitignored):

```
PELOTON_USERNAME=your_email@example.com
PELOTON_PASSWORD=your_password
```

The `pylotoncycle` library handles authentication internally — just pass username and password to `PylotonCycle(username, password)`. It uses the same Auth0 password grant approach as peloton-planner.

### 3. Import Script: `workout_tracker/jobs/import_peloton_workouts.py`

```
Usage: python workout_tracker/jobs/import_peloton_workouts.py
Crontab: 0 6 * * * cd /var/projects/habitz && venv/bin/python workout_tracker/jobs/import_peloton_workouts.py
```

Logic:
1. Initialize pylotoncycle: `conn = PylotonCycle(username, password)`
2. Fetch recent workouts: `workouts = conn.GetRecentWorkouts(10)`
3. Filter: `fitness_discipline == 'cycling'` AND `status == 'COMPLETE'`
4. For each ride not in `peloton_workouts`:
   a. Fetch metrics: `metrics = conn.GetWorkoutMetricsById(workout_id)`
   b. Parse: `parsed = conn.ParseMetricsData(metrics)`
   c. Find or create the user's "Peloton - Main set" Exercise (type='cardio')
   d. Create WorkoutLog with `workout_id` pointing to a Cardio template
   e. Create SetLog with `duration_minutes` = ride duration
   f. Create PelotonWorkout record with rich metrics
5. Log summary: "Imported 2 rides, skipped 5 already imported"

### 4. Data Mapping

| Peloton Field | Habitz Field | Table |
|---------------|--------------|-------|
| `id` | `peloton_workout_id` | peloton_workouts |
| `ride.title` | `ride_title` | peloton_workouts |
| `ride.duration` / 60 | `duration_minutes` | set_logs |
| `start_time` | `started_at` | workout_logs |
| `end_time` | `completed_at` | workout_logs |
| `total_output` | `total_output` | peloton_workouts |
| `calories` | `calories` | peloton_workouts |
| `average_cadence` | `average_cadence` | peloton_workouts |
| `average_heartrate` | `average_heartrate` | peloton_workouts |
| `leaderboard_rank` | `leaderboard_rank` | peloton_workouts |

### 5. WorkoutLog Creation

For each imported Peloton ride:

```python
# Find or use existing Cardio workout template
cardio_workout = Workout.query.filter_by(user_id=user_id, name='Cardio').first()

# Create the log
log = WorkoutLog(
    user_id=user_id,
    workout_id=cardio_workout.id,  # or NULL for free-form
    custom_name=f"Peloton: {ride_title}",
    started_at=ride_start_time,
    completed_at=ride_end_time,
)
db.session.add(log)
db.session.flush()

# Create set log for the ride
set_log = SetLog(
    workout_log_id=log.id,
    exercise_id=peloton_main_set_exercise.id,
    set_number=1,
    duration_minutes=ride_duration_minutes,
    completed=True,
)
db.session.add(set_log)
```

### 6. Deduplication Logic

```python
# Check if already imported
existing = PelotonWorkout.query.filter_by(
    peloton_workout_id=peloton_api_workout_id
).first()

if existing:
    continue  # Skip — already imported
```

### 7. Cron Schedule

Daily at 6:00 AM (before morning workout time):

```
0 6 * * * cd /var/projects/habitz && venv/bin/python workout_tracker/jobs/import_peloton_workouts.py
```

---

## Alternatives Considered

### 1. Direct Peloton API Calls (No Library)

Write a custom API client using `requests` directly.

**Rejected because:**
- Requires maintaining custom code for authentication, token refresh, and API response parsing
- Peloton's unofficial API can change without notice; a library abstracts this
- The user explicitly prefers using a library to minimize maintenance burden

### 2. Real-time Webhook Import

Peloton does not offer webhooks for workout completion events. Would require polling, which is what we're doing anyway.

### 3. Manual Import Button (No Cron)

Add a "Import from Peloton" button to the workout history page that fetches recent rides on demand.

**Rejected as primary approach because:**
- The user explicitly wants automatic daily imports
- Could be added as a secondary feature for manual triggering

### 4. Import All Historical Rides

Fetch the user's entire Peloton workout history on first run.

**Deferred:**
- First implementation imports only recent rides (last 10)
- Historical backfill can be added later with a `--all` flag
- Avoids rate limiting concerns on initial setup

---

## Consequences

### Positive

- **No more manual logging** — Peloton rides appear automatically in Habitz
- **Rich metrics preserved** — output, calories, heart rate stored in `peloton_workouts` table
- **Streak accuracy** — workout counts in the habit dashboard reflect actual Peloton usage
- **Deduplication** — safe to run multiple times; already-imported rides are skipped
- **Minimal schema change** — one new table, no changes to existing tables

### Negative

- **Credential storage** — Peloton username/password must be stored in `.env` (same pattern as other secrets)
- **Library dependency** — `pylotoncycle` is maintained by a solo developer; if abandoned, we may need to fork or maintain our own fork
- **API fragility** — Peloton's unofficial API could change without notice; the library abstracts this but doesn't eliminate the risk

### Risks

- **pylotoncycle abandonment:** The library is maintained by one person as a side project. If it stops being maintained, we can fork it or switch to direct API calls (the API surface is small). Mitigation: the library is simple (~500 lines) and well-documented.
- **Account lockout:** Repeated failed auth attempts could lock the Peloton account. Mitigation: add retry logic with exponential backoff, log failures clearly.

---

## Implementation Plan

### Phase 1: Core Import (MVP)

1. Add `PelotonWorkout` model + migration
2. Create `workout_tracker/jobs/import_peloton_workouts.py`
3. Add `pylotoncycle` to requirements.txt
4. Add Peloton credentials to `.env`
5. Add crontab entry to rawkit-01
6. Test with a single ride import
7. Regression tests

**Backfill:** On first run, fetch 50 rides (~90 days at 3-4 rides/week). The dedup table ensures only new rides are imported. Subsequent daily runs fetch 10 rides (only new ones get processed).

### Phase 2: Enhanced Features (Future)

- Manual "Import from Peloton" button on history page
- Import non-cycling workouts (running, strength, etc.)
- Store performance graph data (cadence/resistance time series)
- Peloton-specific progress charts (output over time, leaderboard rank trends)

---

## Open Questions

1. **Which Cardio workout template to use?** There are 3 identical "Cardio" workouts (ids 4, 5, 6) with different exercise references. Should we consolidate to one, or pick a specific one for imports?

2. **Cool-down handling:** Not all Peloton rides have a cool-down segment. Should we create a cool-down SetLog only when the ride includes one, or always create it with a default duration?

3. **Non-cycling workouts:** The user may also do Peloton running, strength, or yoga classes. Should the MVP support only cycling, or handle all disciplines?

4. **Custom name format:** Should imported rides show as "Peloton: Ride Title" or just the ride title? The custom_name field on WorkoutLog allows flexibility.
