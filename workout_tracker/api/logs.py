from datetime import datetime, timezone

from flask import request, jsonify
from flask_login import login_required, current_user

from .. import db
from . import api_bp
from ..models.log import WorkoutLog, SetLog
from ..models.workout import Workout, WorkoutExercise


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

    log = WorkoutLog(
        user_id=current_user.id,
        workout_id=workout_id,
        program_id=program_id,
    )
    db.session.add(log)
    db.session.flush()

    # Pre-populate sets from workout template
    workout_exercises = (
        WorkoutExercise.query
        .filter_by(workout_id=workout_id)
        .order_by(WorkoutExercise.position)
        .all()
    )

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
            for s in range(1, we.default_sets + 1):
                set_log = SetLog(
                    workout_log_id=log.id,
                    exercise_id=we.exercise_id,
                    set_number=s,
                    planned_reps=we.default_reps,
                    actual_reps=we.default_reps,
                    weight=we.default_weight,
                    completed=False,
                )
                db.session.add(set_log)

    db.session.commit()
    return jsonify(log.to_dict(include_sets=True)), 201


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
                for s in range(1, we.default_sets + 1):
                    set_log = SetLog(
                        workout_log_id=log.id,
                        exercise_id=we.exercise_id,
                        set_number=s,
                        planned_reps=we.default_reps,
                        actual_reps=we.default_reps,
                        weight=we.default_weight,
                        completed=False,
                    )
                    db.session.add(set_log)

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
    for set_log in set_logs:
        log_id = set_log.workout_log_id
        if log_id not in sessions:
            sessions[log_id] = {
                "log_id": log_id,
                "date": set_log.workout_log.started_at.isoformat(),
                "workout_name": set_log.workout_log.custom_name if set_log.workout_log.workout_id is None else set_log.workout_log.workout.name,
                "sets": [],
            }
        sessions[log_id]["sets"].append(set_log.to_dict())

    # Calculate stats for strength exercises
    stats = {"exercise": exercise.to_dict(), "history": list(sessions.values())}

    if exercise.type == "strength":
        # Find PR (personal record) - highest weight
        max_weight = max(
            (s["weight"] for s in set_logs if s["weight"] and s["completed"]),
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
