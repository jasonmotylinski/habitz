from flask import request, jsonify
from flask_login import login_required, current_user

from .. import db
from . import api_bp
from ..models.program import Program, ProgramWorkoutOrder
from ..models.workout import Workout


@api_bp.route("/programs", methods=["GET"])
@login_required
def list_programs():
    programs = Program.query.filter_by(user_id=current_user.id).all()
    return jsonify([p.to_dict(include_workouts=True) for p in programs]), 200


@api_bp.route("/programs", methods=["POST"])
@login_required
def create_program():
    data = request.get_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    program = Program(user_id=current_user.id, name=name)
    db.session.add(program)
    db.session.commit()
    return jsonify(program.to_dict(include_workouts=True)), 201


@api_bp.route("/programs/<int:program_id>", methods=["GET"])
@login_required
def get_program(program_id):
    program = Program.query.filter_by(id=program_id, user_id=current_user.id).first_or_404()
    return jsonify(program.to_dict(include_workouts=True)), 200


@api_bp.route("/programs/<int:program_id>", methods=["PUT"])
@login_required
def update_program(program_id):
    program = Program.query.filter_by(id=program_id, user_id=current_user.id).first_or_404()
    data = request.get_json()

    if "name" in data:
        program.name = data["name"].strip()

    db.session.commit()
    return jsonify(program.to_dict(include_workouts=True)), 200


@api_bp.route("/programs/<int:program_id>", methods=["DELETE"])
@login_required
def delete_program(program_id):
    program = Program.query.filter_by(id=program_id, user_id=current_user.id).first_or_404()
    db.session.delete(program)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200


@api_bp.route("/programs/<int:program_id>/order", methods=["PUT"])
@login_required
def update_program_order(program_id):
    program = Program.query.filter_by(id=program_id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    workout_ids = data.get("workout_ids", [])

    # Clear existing order
    ProgramWorkoutOrder.query.filter_by(program_id=program.id).delete()

    for i, wid in enumerate(workout_ids):
        workout = Workout.query.filter_by(id=wid, user_id=current_user.id).first()
        if workout:
            pwo = ProgramWorkoutOrder(program_id=program.id, workout_id=wid, position=i)
            db.session.add(pwo)

    db.session.commit()
    return jsonify(program.to_dict(include_workouts=True)), 200


@api_bp.route("/programs/<int:program_id>/next", methods=["GET"])
@login_required
def next_workout(program_id):
    from ..models.log import WorkoutLog

    program = Program.query.filter_by(id=program_id, user_id=current_user.id).first_or_404()

    # Get ordered workout ids
    ordered = (
        ProgramWorkoutOrder.query
        .filter_by(program_id=program.id)
        .order_by(ProgramWorkoutOrder.position)
        .all()
    )
    if not ordered:
        return jsonify({"error": "No workouts in program"}), 404

    workout_ids = [o.workout_id for o in ordered]

    # Check for an in-progress (started but not completed) workout log
    in_progress_log = (
        WorkoutLog.query
        .filter_by(user_id=current_user.id, program_id=program.id)
        .filter(WorkoutLog.completed_at.is_(None))
        .order_by(WorkoutLog.started_at.desc())
        .first()
    )

    if in_progress_log and in_progress_log.workout_id in workout_ids:
        # Resume in-progress workout — treat it as the current one
        current_idx = workout_ids.index(in_progress_log.workout_id)
        next_idx = current_idx
    else:
        # Find last completed workout log for this program
        last_log = (
            WorkoutLog.query
            .filter_by(user_id=current_user.id, program_id=program.id)
            .filter(WorkoutLog.completed_at.isnot(None))
            .order_by(WorkoutLog.completed_at.desc())
            .first()
        )

        if last_log and last_log.workout_id in workout_ids:
            last_idx = workout_ids.index(last_log.workout_id)
            next_idx = (last_idx + 1) % len(workout_ids)
        else:
            next_idx = 0

    next_workout_id = workout_ids[next_idx]
    workout = db.session.get(Workout, next_workout_id)

    # Build upcoming schedule
    upcoming = []
    for i in range(len(workout_ids)):
        idx = (next_idx + i) % len(workout_ids)
        w = db.session.get(Workout, workout_ids[idx])
        upcoming.append(w.to_dict(include_exercises=True))

    result = {
        "next_workout": workout.to_dict(include_exercises=True),
        "upcoming": upcoming,
        "program": program.to_dict(),
    }

    # Include in-progress log id so the home page can resume it
    if in_progress_log and in_progress_log.workout_id in workout_ids:
        result["in_progress_log_id"] = in_progress_log.id

    return jsonify(result), 200
