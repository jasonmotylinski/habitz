import logging
from datetime import datetime, timezone, timedelta
from collections import Counter

from flask import request, jsonify
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)

from .. import db
from . import api_bp
from ..models.log import WorkoutLog, SetLog
from ..models.workout import Workout, WorkoutExercise


def get_last_weights_for_workout(workout_id, user_id):
    """
    Get the most recent weights used for each exercise in a completed workout.
    Returns a dict mapping exercise_id -> weight.
    """
    last_log = (
        WorkoutLog.query
        .filter_by(user_id=user_id, workout_id=workout_id)
        .filter(WorkoutLog.completed_at.isnot(None))
        .order_by(WorkoutLog.started_at.desc())
        .first()
    )
    
    if not last_log:
        return {}
    
    # Get the last weight used for each exercise in that log
    weights_by_exercise = {}
    for set_log in last_log.sets:
        if set_log.weight and set_log.exercise_id not in weights_by_exercise:
            weights_by_exercise[set_log.exercise_id] = set_log.weight
    
    return weights_by_exercise


def session_strength_flags(session_set_logs):
    """
    Given one session's SetLog rows, return (top_weight, hit_reps_target).

    - top_weight: heaviest weight among completed sets (None if none).
    - hit_reps_target: True only if every completed working set at
      top_weight reached its planned reps. This gates the weight-bump
      recommendation: same weight 3 sessions in a row only earns a bump
      when the target reps were actually hit each time.
    """
    done = [s for s in session_set_logs if s.completed and s.weight]
    top_weight = max((s.weight for s in done), default=None)
    hit_reps_target = bool(top_weight) and all(
        s.planned_reps is not None
        and s.actual_reps is not None
        and s.actual_reps >= s.planned_reps
        for s in done
        if s.weight == top_weight
    )
    return top_weight, hit_reps_target


@api_bp.route("/logs", methods=["GET"])
@login_required
def list_logs():
    from_date = request.args.get("from")
    to_date = request.args.get("to")

    query = WorkoutLog.query.filter_by(user_id=current_user.id)

    if from_date:
        query = query.filter(WorkoutLog.started_at >= from_date)
    if to_date:
        query = query.filter(WorkoutLog.started_at <= to_date)

    logs = query.order_by(WorkoutLog.started_at.desc()).all()
    return jsonify([log.to_dict(include_sets=True) for log in logs]), 200


@api_bp.route("/logs/calendar", methods=["GET"])
@login_required
def calendar():
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)

    if not month or not year:
        now = datetime.now(timezone.utc)
        month = month or now.month
        year = year or now.year

    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

    logs = (
        WorkoutLog.query
        .filter_by(user_id=current_user.id)
        .filter(WorkoutLog.started_at >= start, WorkoutLog.started_at < end)
        .all()
    )

    dates = list(set(log.started_at.strftime("%Y-%m-%d") for log in logs))
    return jsonify({"month": month, "year": year, "workout_dates": sorted(dates)}), 200


@api_bp.route("/logs", methods=["POST"])
@login_required
def start_workout():
    data = request.get_json()
    workout_id = data.get("workout_id")
    program_id = data.get("program_id")
    custom_name = data.get("custom_name")

    # Quick log: ad-hoc workout with just a name
    if custom_name and not workout_id:
        custom_name = custom_name.strip()
        if not custom_name:
            return jsonify({"error": "Workout name is required"}), 400
        log = WorkoutLog(
            user_id=current_user.id,
            custom_name=custom_name,
            notes=data.get("notes"),
            completed_at=datetime.now(timezone.utc),
        )
        db.session.add(log)
        db.session.commit()
        return jsonify(log.to_dict()), 201

    if not workout_id:
        return jsonify({"error": "workout_id or custom_name is required"}), 400

    workout = Workout.query.filter_by(id=workout_id, user_id=current_user.id).first()
    if not workout:
        return jsonify({"error": "Workout not found"}), 404

    # Return existing incomplete log instead of creating a duplicate
    existing = (
        WorkoutLog.query
        .filter_by(user_id=current_user.id, workout_id=workout_id)
        .filter(WorkoutLog.completed_at.is_(None))
        .first()
    )
    if existing:
        # Fetch the current workout template exercises (needed below and for new log)
        workout_exercises = (
            WorkoutExercise.query
            .filter_by(workout_id=workout_id)
            .order_by(WorkoutExercise.position)
            .all()
        )
        template_exercise_ids = {we.exercise_id for we in workout_exercises}

        # Remove any sets that don't belong to this workout's template.
        # This cleans up corruption from concurrent workout-switch requests.
        removed = False
        for s in existing.sets.all():
            if s.exercise_id not in template_exercise_ids:
                db.session.delete(s)
                removed = True

        if removed:
            logger.warning(
                '[start_workout] removed stale sets from existing log=%d workout_id=%s',
                existing.id, workout_id,
            )
            db.session.commit()

        return jsonify(existing.to_dict(include_sets=True)), 200

    log = WorkoutLog(
        user_id=current_user.id,
        workout_id=workout_id,
        program_id=program_id,
    )
    db.session.add(log)
    db.session.flush()

    # Purge any orphaned set_logs that survived a previous delete of a log
    # with this recycled ID (SQLite reuses IDs; ORM cascade may not have fired).
    stale = SetLog.query.filter_by(workout_log_id=log.id).all()
    if stale:
        logger.warning(
            '[start_workout] purging %d orphaned sets for recycled log_id=%d',
            len(stale), log.id,
        )
        for s in stale:
            db.session.delete(s)
        db.session.flush()

    # Pre-populate sets from workout template
    workout_exercises = (
        WorkoutExercise.query
        .filter_by(workout_id=workout_id)
        .order_by(WorkoutExercise.position)
        .all()
    )

    # Get last weights used for this workout
    last_weights = get_last_weights_for_workout(workout_id, current_user.id)

    for we in workout_exercises:
        if we.exercise.type == "cardio":
            set_log = SetLog(
                workout_log_id=log.id,
                exercise_id=we.exercise_id,
                set_number=1,
                duration_minutes=we.default_duration_minutes,
                completed=False,
            )
            db.session.add(set_log)
        else:
            # Use last weight if available, otherwise use default
            weight = last_weights.get(we.exercise_id, we.default_weight)
            for s in range(1, we.default_sets + 1):
                set_log = SetLog(
                    workout_log_id=log.id,
                    exercise_id=we.exercise_id,
                    set_number=s,
                    planned_reps=we.default_reps,
                    actual_reps=we.default_reps,
                    weight=weight,
                    completed=False,
                )
                db.session.add(set_log)

    db.session.commit()
    result = log.to_dict(include_sets=True)
    exercise_ids = list({s['exercise_id'] for s in result.get('sets', [])})
    logger.info('[start_workout] log=%d workout_id=%s sets=%d exercise_ids=%s',
                log.id, workout_id, len(result.get('sets', [])), exercise_ids)
    return jsonify(result), 201


@api_bp.route("/logs/<int:log_id>", methods=["GET"])
@login_required
def get_log(log_id):
    log = WorkoutLog.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    return jsonify(log.to_dict(include_sets=True)), 200


@api_bp.route("/logs/<int:log_id>", methods=["PUT"])
@login_required
def update_log(log_id):
    log = WorkoutLog.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    data = request.get_json()

    if "workout_id" in data:
        new_workout_id = data["workout_id"]
        new_workout = Workout.query.filter_by(id=new_workout_id, user_id=current_user.id).first_or_404()

        # Clear existing sets if switching workout
        for s in log.sets.all():
            db.session.delete(s)
        db.session.flush()

        # Update the workout
        log.workout_id = new_workout_id

        # Pre-populate sets from new workout template
        workout_exercises = (
            WorkoutExercise.query
            .filter_by(workout_id=new_workout_id)
            .order_by(WorkoutExercise.position)
            .all()
        )

        # Get last weights used for new workout
        last_weights = get_last_weights_for_workout(new_workout_id, current_user.id)

        for we in workout_exercises:
            if we.exercise.type == "cardio":
                set_log = SetLog(
                    workout_log_id=log.id,
                    exercise_id=we.exercise_id,
                    set_number=1,
                    duration_minutes=we.default_duration_minutes,
                    completed=False,
                )
                db.session.add(set_log)
            else:
                # Use last weight if available, otherwise use default
                weight = last_weights.get(we.exercise_id, we.default_weight)
                for s in range(1, we.default_sets + 1):
                    set_log = SetLog(
                        workout_log_id=log.id,
                        exercise_id=we.exercise_id,
                        set_number=s,
                        planned_reps=we.default_reps,
                        actual_reps=we.default_reps,
                        weight=weight,
                        completed=False,
                    )
                    db.session.add(set_log)

    if "started_at" in data:
        try:
            new_date = datetime.fromisoformat(data["started_at"].replace("Z", "+00:00"))
            log.started_at = new_date
            if log.completed_at:
                log.completed_at = new_date
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400
    if "notes" in data:
        log.notes = data["notes"]
    if "body_weight" in data:
        log.body_weight = data["body_weight"]
    if data.get("complete"):
        log.completed_at = datetime.now(timezone.utc)

    db.session.commit()
    return jsonify(log.to_dict(include_sets=True)), 200


@api_bp.route("/logs/<int:log_id>/sets/<int:set_id>", methods=["PUT"])
@login_required
def update_set(log_id, set_id):
    log = WorkoutLog.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    set_log = SetLog.query.filter_by(id=set_id, workout_log_id=log.id).first_or_404()
    data = request.get_json()

    if "actual_reps" in data:
        set_log.actual_reps = data["actual_reps"]
    if "weight" in data:
        set_log.weight = data["weight"]
    if "duration_minutes" in data:
        set_log.duration_minutes = data["duration_minutes"]
    if "completed" in data:
        set_log.completed = data["completed"]

    db.session.commit()
    return jsonify(set_log.to_dict()), 200


@api_bp.route("/logs/<int:log_id>/sets/<int:set_id>", methods=["DELETE"])
@login_required
def delete_set(log_id, set_id):
    log = WorkoutLog.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    set_log = SetLog.query.filter_by(id=set_id, workout_log_id=log.id).first_or_404()
    db.session.delete(set_log)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200


@api_bp.route("/logs/<int:log_id>", methods=["DELETE"])
@login_required
def delete_log(log_id):
    log = WorkoutLog.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    db.session.delete(log)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200


@api_bp.route("/workouts/<int:workout_id>/last-weights", methods=["GET"])
@login_required
def get_workout_last_weights(workout_id):
    """Get the last weights used for each exercise in the most recent completed workout."""
    workout = Workout.query.filter_by(id=workout_id, user_id=current_user.id).first_or_404()
    weights = get_last_weights_for_workout(workout_id, current_user.id)
    return jsonify(weights), 200


@api_bp.route("/exercises/<int:exercise_id>/progress", methods=["GET"])
@login_required
def exercise_progress(exercise_id):
    from ..models.exercise import Exercise

    exercise = Exercise.query.filter_by(id=exercise_id, user_id=current_user.id).first_or_404()

    # Get all set logs for this exercise
    set_logs = (
        SetLog.query
        .filter_by(exercise_id=exercise_id)
        .join(WorkoutLog)
        .filter(WorkoutLog.user_id == current_user.id)
        .order_by(WorkoutLog.started_at.desc())
        .all()
    )

    if not set_logs:
        return jsonify({"exercise": exercise.to_dict(), "history": []}), 200

    # Group by workout log for display
    sessions = {}
    session_set_logs = {}
    for set_log in set_logs:
        log_id = set_log.workout_log_id
        if log_id not in sessions:
            sessions[log_id] = {
                "log_id": log_id,
                "date": set_log.workout_log.started_at.isoformat(),
                "workout_name": set_log.workout_log.custom_name if set_log.workout_log.workout_id is None else set_log.workout_log.workout.name,
                "sets": [],
            }
            session_set_logs[log_id] = []
        sessions[log_id]["sets"].append(set_log.to_dict())
        session_set_logs[log_id].append(set_log)

    if exercise.type == "strength":
        # Per-session flags consumed by the plateau/bump UI in
        # active_workout.html — a weight bump is only recommended when
        # the planned reps were hit at the top weight.
        for log_id, session in sessions.items():
            top_weight, hit_reps_target = session_strength_flags(session_set_logs[log_id])
            session["top_weight"] = top_weight
            session["hit_reps_target"] = hit_reps_target

    # Calculate stats for strength exercises
    stats = {"exercise": exercise.to_dict(), "history": list(sessions.values())}

    if exercise.type == "strength":
        # Find PR (personal record) - highest weight
        max_weight = max(
            (s.weight for s in set_logs if s.weight and s.completed),
            default=None,
        )
        if max_weight:
            stats["pr"] = max_weight

        # Get recent PRs (last 3 sessions with weight)
        recent_weights = []
        seen_weights = set()
        for set_log in set_logs:
            if set_log.weight and set_log.completed:
                w = set_log.weight
                if w not in seen_weights:
                    recent_weights.append(w)
                    seen_weights.add(w)
                if len(recent_weights) >= 3:
                    break
        stats["recent_weights"] = recent_weights
    else:
        # For cardio, show recent durations
        recent_durations = []
        seen_durations = set()
        for set_log in set_logs:
            if set_log.duration_minutes and set_log.completed:
                d = set_log.duration_minutes
                if d not in seen_durations:
                    recent_durations.append(d)
                    seen_durations.add(d)
                if len(recent_durations) >= 3:
                    break
        stats["recent_durations"] = recent_durations

    return jsonify(stats), 200


@api_bp.route("/logs/frequency", methods=["GET"])
@login_required
def workout_frequency():
    """
    Return workout counts aggregated by time period for frequency charts.

    Query params:
        period: week (last 12 weeks), month (last 12 months), year (all years)

    Returns:
        { period, data: [{ label, count }], stats: { total, avg_per_week, current_streak, best_streak } }
    """
    period = request.args.get("period", "week")
    now = datetime.utcnow()

    # Fetch all completed logs for the user
    all_logs = (
        WorkoutLog.query
        .filter_by(user_id=current_user.id)
        .filter(WorkoutLog.completed_at.isnot(None))
        .order_by(WorkoutLog.started_at.asc())
        .all()
    )

    if not all_logs:
        return jsonify({
            "period": period,
            "data": [],
            "stats": {"total": 0, "avg_per_week": 0, "current_streak": 0, "best_streak": 0},
        }), 200

    # --- Build period buckets ---

    if period == "week":
        # Last 12 weeks
        start = now - timedelta(weeks=11, days=now.weekday())  # start of week 12 weeks ago
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)

        counts = Counter()
        for log in all_logs:
            if log.started_at < start:
                continue
            iso = log.started_at.isocalendar()
            counts[f"{iso[0]}-W{iso[1]:02d}"] += 1

        data = []
        for i in range(12):
            week_start = start + timedelta(weeks=i)
            iso = week_start.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
            label = week_start.strftime("%b %d")
            data.append({"label": label, "count": counts.get(key, 0)})

    elif period == "month":
        # Last 12 months
        start = (now.replace(day=1) - timedelta(days=365)).replace(hour=0, minute=0, second=0, microsecond=0)

        counts = Counter()
        for log in all_logs:
            if log.started_at < start:
                continue
            counts[log.started_at.strftime("%Y-%m")] += 1

        data = []
        for i in range(12):
            # Walk forward from start
            month = (start.month - 1 + i) % 12 + 1
            year = start.year + (start.month - 1 + i) // 12
            key = f"{year}-{month:02d}"
            label = datetime(year, month, 1).strftime("%b")
            data.append({"label": label, "count": counts.get(key, 0)})

    else:  # year
        counts = Counter()
        for log in all_logs:
            counts[str(log.started_at.year)] += 1

        min_year = min(int(k) for k in counts.keys())
        max_year = now.year
        data = []
        for y in range(min_year, max_year + 1):
            key = str(y)
            data.append({"label": key, "count": counts.get(key, 0)})

    # --- Stats ---

    # Avg per week: use actual date span of all logs
    first_date = all_logs[0].started_at
    last_date = all_logs[-1].started_at
    weeks_span = max(1, (last_date - first_date).days / 7)
    avg_per_week = round(len(all_logs) / weeks_span, 1)

    # Streaks: consecutive non-zero periods from end (current), longest run (best)
    current_streak = 0
    for d in reversed(data):
        if d["count"] > 0:
            current_streak += 1
        else:
            break

    best_streak = 0
    streak = 0
    for d in data:
        if d["count"] > 0:
            streak += 1
            best_streak = max(best_streak, streak)
        else:
            streak = 0

    return jsonify({
        "period": period,
        "data": data,
        "stats": {
            "total": len(all_logs),
            "avg_per_week": avg_per_week,
            "current_streak": current_streak,
            "best_streak": best_streak,
        },
    }), 200
