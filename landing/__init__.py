from flask import Flask, render_template
from flask_login import LoginManager, current_user


def create_app():
    from dotenv import load_dotenv
    load_dotenv()

    app = Flask(__name__)

    from .config import Config
    app.config.from_object(Config)

    from shared import db, User
    db.init_app(app)

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

    @app.route('/')
    def index():
        return render_template('index.html', user=current_user)

    return app
