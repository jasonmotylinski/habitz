from flask import Flask, jsonify, request, redirect, session
from flask_migrate import Migrate
from flask_login import LoginManager

from shared import db
from .config import config

migrate = Migrate()
login_manager = LoginManager()


def create_app(config_name=None):
    if config_name is None:
        import os
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @app.before_request
    def make_session_permanent():
        session.permanent = True

    @login_manager.user_loader
    def load_user(user_id):
        from shared.user import User
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/"):
            return jsonify({"error": "Login required"}), 401
        next_path = request.script_root + request.path
        return redirect(f'/login?next={next_path}')

    from .models import user  # noqa: F401 - register models

    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    from .views import views_bp
    app.register_blueprint(views_bp)

    with app.app_context():
        db.create_all()

    return app
