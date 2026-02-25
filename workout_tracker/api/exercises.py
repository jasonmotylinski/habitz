from flask import request, jsonify
from flask_login import login_required, current_user

from .. import db
from . import api_bp
from ..models.exercise import Exercise


@api_bp.route("/exercises", methods=["GET"])
@login_required
def list_exercises():
    exercises = Exercise.query.filter_by(user_id=current_user.id).all()
    return jsonify([e.to_dict() for e in exercises]), 200


@api_bp.route("/exercises", methods=["POST"])
@login_required
def create_exercise():
    data = request.get_json()
    name = data.get("name", "").strip()
    ex_type = data.get("type", "strength")
    unit = data.get("unit", "reps")

    if not name:
        return jsonify({"error": "Name is required"}), 400
    if ex_type not in ("strength", "cardio"):
        return jsonify({"error": "Type must be 'strength' or 'cardio'"}), 400
    if unit not in ("reps", "secs", "mins"):
        return jsonify({"error": "Unit must be 'reps', 'secs', or 'mins'"}), 400

    exercise = Exercise(user_id=current_user.id, name=name, type=ex_type, unit=unit)
    db.session.add(exercise)
    db.session.commit()
    return jsonify(exercise.to_dict()), 201


@api_bp.route("/exercises/<int:exercise_id>", methods=["PUT"])
@login_required
def update_exercise(exercise_id):
    exercise = Exercise.query.filter_by(id=exercise_id, user_id=current_user.id).first_or_404()
    data = request.get_json()

    if "name" in data:
        exercise.name = data["name"].strip()
    if "type" in data and data["type"] in ("strength", "cardio"):
        exercise.type = data["type"]
    if "unit" in data and data["unit"] in ("reps", "secs", "mins"):
        exercise.unit = data["unit"]

    db.session.commit()
    return jsonify(exercise.to_dict()), 200


@api_bp.route("/exercises/<int:exercise_id>", methods=["DELETE"])
@login_required
def delete_exercise(exercise_id):
    exercise = Exercise.query.filter_by(id=exercise_id, user_id=current_user.id).first_or_404()
    db.session.delete(exercise)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200
