from flask import Flask
from flask_login import LoginManager


def create_app(config_name='development'):
    from dotenv import load_dotenv
    import os

    if 'DATABASE_URL' not in os.environ:
        load_dotenv()

    app = Flask(__name__, static_folder='static', static_url_path='/static')

    from .config import config
    app.config.from_object(config[config_name])

    from shared import db, User
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import redirect, request, jsonify
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'Login required'}), 401
        next_path = request.script_root + request.path
        return redirect(f'/login?next={next_path}')

    from .main import main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        from meal_planner.models import Household  # noqa: F401 — needed so FK resolves
        from workout_tracker.models import Program, Workout, Exercise, WorkoutLog  # noqa: F401
        from calorie_tracker.models import FoodLog  # noqa: F401
        from fasting_tracker.models import Fast, MicroFast  # noqa: F401
        db.create_all()

    return app
