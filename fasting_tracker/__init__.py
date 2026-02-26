from flask import Flask, redirect, request, session
from flask_login import LoginManager
from flask_migrate import Migrate

from .config import config

migrate = Migrate()


def create_app(config_name='development'):
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object(config[config_name])

    from shared import db, User
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)

    @app.before_request
    def make_session_permanent():
        session.permanent = True

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.is_json or request.path.startswith('/api/'):
            from flask import jsonify
            return jsonify({'error': 'Login required'}), 401
        next_path = request.script_root + request.path
        return redirect(f'/login?next={next_path}')

    from .main import main_bp
    from .api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()

    return app
