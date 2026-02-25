from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from .forms import GoalsForm
from .models import db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('home.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@main_bp.route('/history')
@login_required
def history():
    return render_template('history.html')


@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = GoalsForm(obj=current_user)
    if form.validate_on_submit():
        current_user.default_fast_hours = form.default_fast_hours.data
        db.session.commit()
        flash('Settings saved.', 'success')
        return redirect(url_for('main.settings'))
    return render_template('settings.html', form=form)
