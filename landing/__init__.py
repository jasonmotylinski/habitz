from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate

migrate = Migrate()


def create_app():
    from dotenv import load_dotenv
    import os

    # Only load .env if DATABASE_URL is not already set (e.g., during tests or with explicit env vars)
    if 'DATABASE_URL' not in os.environ:
        load_dotenv()

    app = Flask(__name__)

    from .config import Config
    app.config.from_object(Config)

    from shared import db, User
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so Migrate sees them
    from . import models  # noqa: F401

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import redirect
        return redirect('/login')

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    from .habits import habits_bp
    app.register_blueprint(habits_bp)

    from .api import api_bp
    app.register_blueprint(api_bp)

    return app
