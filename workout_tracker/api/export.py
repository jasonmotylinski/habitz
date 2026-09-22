"""Apple Health export endpoint (consumed by an iOS Shortcut).

Auth: session cookie OR Bearer token (user.apple_health_token).
Server stays stateless: the Shortcut stores its own last-sync cursor and
passes it as ?since=; the response's `now` becomes the next cursor.
"""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from flask import request, jsonify
from flask_login import current_user

from . import api_bp
from ..models.user import User
from ..models.log import WorkoutLog, PelotonWorkout


def _resolve_user():
    """Session cookie auth, falling back to Bearer token auth."""
    if current_user.is_authenticated:
        return current_user
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[len("Bearer "):].strip()
        return User.query.filter_by(apple_health_token=token).first()
    return None


def _aware_utc(dt):
    """SQLite may hand back naive datetimes; they are stored in UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@api_bp.route("/export/apple-health", methods=["GET"])
def export_apple_health():
    now = datetime.now(timezone.utc)  # captured at request start (race avoidance)

    user = _resolve_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    tz = ZoneInfo(user.timezone or "America/New_York")

    # since: ISO date (or datetime); default last 30 days. Filtered in Python
    # so the user's local midnight is honored regardless of SQLite string quirks.
    since_raw = request.args.get("since")
    if since_raw:
        try:
            since_dt = datetime.fromisoformat(since_raw)
        except ValueError:
            return jsonify({"error": "invalid since; expected ISO date"}), 400
        if since_dt.tzinfo is None:
            # interpret bare dates as local midnight in the user's timezone
            since_dt = since_dt.replace(tzinfo=tz)
    else:
        since_dt = now.astimezone(tz) - timedelta(days=30)

    logs = (
        WorkoutLog.query
        .filter_by(user_id=user.id)
        .filter(WorkoutLog.completed_at.isnot(None))
        .order_by(WorkoutLog.started_at.asc())
        .all()
    )

    log_ids = [log.id for log in logs]
    # Peloton-imported rides are excluded: the Peloton app syncs them to
    # HealthKit natively, and logging them here would duplicate every ride.
    peloton_linked = {
        p.workout_log_id
        for p in PelotonWorkout.query.filter(
            PelotonWorkout.workout_log_id.in_(log_ids)
        ).all()
    } if log_ids else set()

    def iso_local(dt):
        return _aware_utc(dt).astimezone(tz).isoformat()

    workouts = []
    for log in logs:
        started = _aware_utc(log.started_at)
        completed = _aware_utc(log.completed_at)
        if started < since_dt:
            continue

        if log.id in peloton_linked:
            continue

        is_strength = any(s.exercise.type == "strength" for s in log.sets)
        hk_type = "traditional_strength_training" if is_strength else "functional_strength_training"
        name = log.custom_name or (log.workout.name if log.workout_id else "Workout")
        calories = None

        workouts.append({
            "name": name,
            "hk_type": hk_type,
            "start": iso_local(started),
            "end": iso_local(completed),
            # floor-div of a tiny negative skew (completed_at just before
            # started_at, seen in manually-logged workouts) yields -1 — clamp to 1.
            # Never emit 0: iOS Shortcuts' Log Workout action aborts the whole
            # batch on a zero-duration workout (observed: the import stopped at a
            # same-minute "Hotel" log and dropped every workout after it), so the
            # export floor is 1 minute.
            "duration_minutes": max(1, int((completed - started).total_seconds() // 60)),
            "calories": calories,
        })

    return jsonify({
        "workouts": workouts,
        "now": now.astimezone(tz).isoformat(),
    })
