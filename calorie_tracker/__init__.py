from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate

from .config import config

migrate = Migrate()


def create_app(config_name='development'):
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object(config[config_name])

    from .models import db, User
    db.init_app(app)
    migrate.init_app(app, db)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .auth import auth_bp
    from .main import main_bp
    from .food import food_bp
    from .api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(food_bp)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()

    return app
