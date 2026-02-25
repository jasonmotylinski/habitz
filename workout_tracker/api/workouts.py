from flask import request, jsonify
from flask_login import login_required, current_user

from .. import db
from . import api_bp
from ..models.workout import Workout, WorkoutExercise
from ..models.exercise import Exercise


@api_bp.route("/workouts", methods=["GET"])
@login_required
def list_workouts():
    workouts = Workout.query.filter_by(user_id=current_user.id).all()
    return jsonify([w.to_dict(include_exercises=True) for w in workouts]), 200


@api_bp.route("/workouts", methods=["POST"])
@login_required
def create_workout():
    data = request.get_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    workout = Workout(user_id=current_user.id, name=name)
    db.session.add(workout)
    db.session.commit()
    return jsonify(workout.to_dict(include_exercises=True)), 201


@api_bp.route("/workouts/<int:workout_id>", methods=["GET"])
@login_required
def get_workout(workout_id):
    workout = Workout.query.filter_by(id=workout_id, user_id=current_user.id).first_or_404()
    return jsonify(workout.to_dict(include_exercises=True)), 200


@api_bp.route("/workouts/<int:workout_id>", methods=["PUT"])
@login_required
def update_workout(workout_id):
    workout = Workout.query.filter_by(id=workout_id, user_id=current_user.id).first_or_404()
    data = request.get_json()

    if "name" in data:
        workout.name = data["name"].strip()

    db.session.commit()
    return jsonify(workout.to_dict(include_exercises=True)), 200


@api_bp.route("/workouts/<int:workout_id>", methods=["DELETE"])
@login_required
def delete_workout(workout_id):
    workout = Workout.query.filter_by(id=workout_id, user_id=current_user.id).first_or_404()
    db.session.delete(workout)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200


@api_bp.route("/workouts/<int:workout_id>/exercises", methods=["PUT"])
@login_required
def update_workout_exercises(workout_id):
    workout = Workout.query.filter_by(id=workout_id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    exercises_data = data.get("exercises", [])

    # Clear existing
    WorkoutExercise.query.filter_by(workout_id=workout.id).delete()

    for i, ex in enumerate(exercises_data):
        exercise = Exercise.query.filter_by(id=ex["exercise_id"], user_id=current_user.id).first()
        if not exercise:
            continue
        we = WorkoutExercise(
            workout_id=workout.id,
            exercise_id=exercise.id,
            position=i,
            default_sets=ex.get("default_sets", 5),
            default_reps=ex.get("default_reps", 5),
            default_weight=ex.get("default_weight"),
            default_duration_minutes=ex.get("default_duration_minutes"),
            unit=ex.get("unit", "reps"),
        )
        db.session.add(we)

    db.session.commit()
    return jsonify(workout.to_dict(include_exercises=True)), 200


@api_bp.route("/workouts/<int:workout_id>/exercises", methods=["POST"])
@login_required
def add_exercise_to_workout(workout_id):
    workout = Workout.query.filter_by(id=workout_id, user_id=current_user.id).first_or_404()
    data = request.get_json()

    exercise = Exercise.query.filter_by(id=data["exercise_id"], user_id=current_user.id).first()
    if not exercise:
        return jsonify({"error": "Exercise not found"}), 404

    max_pos = db.session.query(db.func.max(WorkoutExercise.position)).filter_by(workout_id=workout.id).scalar()
    position = (max_pos or 0) + 1

    we = WorkoutExercise(
        workout_id=workout.id,
        exercise_id=exercise.id,
        position=position,
        default_sets=data.get("default_sets", 5),
        default_reps=data.get("default_reps", 5),
        default_weight=data.get("default_weight"),
        default_duration_minutes=data.get("default_duration_minutes"),
        unit=data.get("unit", "reps"),
    )
    db.session.add(we)
    db.session.commit()
    return jsonify(workout.to_dict(include_exercises=True)), 201


@api_bp.route("/workouts/<int:workout_id>/exercises/<int:we_id>", methods=["PUT"])
@login_required
def update_workout_exercise(workout_id, we_id):
    workout = Workout.query.filter_by(id=workout_id, user_id=current_user.id).first_or_404()
    we = WorkoutExercise.query.filter_by(id=we_id, workout_id=workout.id).first_or_404()
    data = request.get_json()

    if "exercise_name" in data:
        we.exercise.name = data["exercise_name"]
    if "default_sets" in data:
        we.default_sets = data["default_sets"]
    if "default_reps" in data:
        we.default_reps = data["default_reps"]
    if "default_weight" in data:
        we.default_weight = data["default_weight"]
    if "default_duration_minutes" in data:
        we.default_duration_minutes = data["default_duration_minutes"]
    if "unit" in data:
        we.unit = data["unit"]

    db.session.commit()
    return jsonify(workout.to_dict(include_exercises=True)), 200


@api_bp.route("/workouts/<int:workout_id>/exercises/<int:we_id>", methods=["DELETE"])
@login_required
def remove_exercise_from_workout(workout_id, we_id):
    workout = Workout.query.filter_by(id=workout_id, user_id=current_user.id).first_or_404()
    we = WorkoutExercise.query.filter_by(id=we_id, workout_id=workout.id).first_or_404()
    db.session.delete(we)
    db.session.commit()
    return jsonify(workout.to_dict(include_exercises=True)), 200
