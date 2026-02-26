from flask import Flask, jsonify, request, redirect, url_for, session
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

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/"):
            return jsonify({"error": "Login required"}), 401
        return redirect(url_for("views.login"))

    from .models import user  # noqa: F401 - register models

    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    from .views import views_bp
    app.register_blueprint(views_bp)

    with app.app_context():
        db.create_all()

    return app
