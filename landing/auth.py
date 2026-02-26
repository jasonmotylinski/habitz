from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request
from flask_login import current_user, login_required, login_user, logout_user

from shared import db
from shared.user import User

from .forms import LoginForm, RegistrationForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(_safe_next() or '/')

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=True)
            return redirect(_safe_next() or '/')
        flash('Invalid email or password.', 'danger')

    return render_template('login.html', form=form)


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect('/login')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect('/')

    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
        elif User.query.filter_by(username=form.username.data).first():
            flash('Username already taken.', 'danger')
        else:
            user = User(username=form.username.data, email=email)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            return redirect('/')

    return render_template('register.html', form=form)


def _safe_next():
    """Return the `next` query param only if it's a safe relative path."""
    next_url = request.args.get('next', '')
    parsed = urlparse(next_url)
    # Allow only relative paths (no scheme/netloc = same-origin)
    if next_url and not parsed.scheme and not parsed.netloc and next_url.startswith('/'):
        return next_url
    return None
