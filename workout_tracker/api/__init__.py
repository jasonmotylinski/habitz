from flask import Blueprint

api_bp = Blueprint("api", __name__)

from . import auth, programs, workouts, exercises, logs  # noqa: F401, E402
