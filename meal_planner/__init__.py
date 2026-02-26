from flask import Flask, send_from_directory, redirect, request
from flask_login import LoginManager
from flask_migrate import Migrate
from .config import config
import os

migrate = Migrate()


def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object(config[config_name])

    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Serve uploaded files
    @app.route('/static/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Initialize extensions
    from shared import db, User
    db.init_app(app)
    migrate.init_app(app, db)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        next_path = request.script_root + request.path
        return redirect(f'/login?next={next_path}')

    # Register blueprints
    from .main import main_bp
    from .meals import meals_bp
    from .planner import planner_bp
    from .shopping import shopping_bp
    from .household import household_bp
    from .api import api_bp
    from .api_keys import api_keys_bp
    from .settings import settings_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(meals_bp)
    app.register_blueprint(planner_bp)
    app.register_blueprint(shopping_bp)
    app.register_blueprint(household_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(api_keys_bp)
    app.register_blueprint(settings_bp)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app
