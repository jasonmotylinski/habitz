from flask import Blueprint, render_template
from flask_login import login_required, current_user

views_bp = Blueprint("views", __name__)


@views_bp.route("/login")
def login():
    if current_user.is_authenticated:
        return render_template("home.html")
    return render_template("login.html")


@views_bp.route("/register")
def register():
    if current_user.is_authenticated:
        return render_template("home.html")
    return render_template("register.html")


@views_bp.route("/")
@login_required
def home():
    return render_template("home.html")


@views_bp.route("/programs")
@login_required
def programs():
    return render_template("programs.html")


@views_bp.route("/programs/<int:program_id>")
@login_required
def program_detail(program_id):
    return render_template("program_detail.html", program_id=program_id)


@views_bp.route("/workouts/<int:workout_id>/edit")
@login_required
def workout_edit(workout_id):
    return render_template("workout_edit.html", workout_id=workout_id)


@views_bp.route("/workout/<int:log_id>/active")
@login_required
def active_workout(log_id):
    return render_template("active_workout.html", log_id=log_id)


@views_bp.route("/quick-log")
@login_required
def quick_log():
    return render_template("quick_log.html")


@views_bp.route("/history")
@login_required
def history():
    return render_template("history.html")


@views_bp.route("/exercises/<int:exercise_id>/progress")
@login_required
def exercise_progress(exercise_id):
    return render_template("exercise_progress.html", exercise_id=exercise_id)
