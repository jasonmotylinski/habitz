from datetime import date

from flask import Blueprint, flash, redirect, render_template, request
from flask_login import current_user, login_required

from shared import db

from .completion import check_completion, current_streak, sync_app_linked
from .models import Habit, HabitLog

habits_bp = Blueprint('habits', __name__)

APP_LINKED_DEFAULTS = [
    {'name': 'Work out',        'habit_type': 'workout',  'icon': '🏋️', 'color': '#E2844A'},
    {'name': 'Hit calorie goal','habit_type': 'calories', 'icon': '🔥', 'color': '#E2C44A'},
    {'name': 'Complete a fast', 'habit_type': 'fasting',  'icon': '⏱️', 'color': '#4AE2B4'},
    {'name': 'Plan meals',      'habit_type': 'meals',    'icon': '🍽️', 'color': '#4A90E2'},
]

APP_LINKS = {
    'workout':  '/workouts/',
    'calories': '/calories/',
    'fasting':  '/fasting/',
    'meals':    '/meals/',
}


@habits_bp.route('/history')
@login_required
def history():
    return render_template('history.html', user=current_user)


@habits_bp.route('/')
@login_required
def index():
    today = date.today()
    habits = (
        Habit.query
        .filter_by(user_id=current_user.id, active=True)
        .order_by(Habit.sort_order, Habit.created_at)
        .all()
    )

    # Sync app-linked habits
    for habit in habits:
        if habit.habit_type != 'manual':
            sync_app_linked(habit, current_user, today)

    # Build display data
    habit_data = []
    for habit in habits:
        done = check_completion(habit, current_user, today)
        streak = current_streak(habit.id)
        habit_data.append({
            'habit':  habit,
            'done':   done,
            'streak': streak,
            'link':   APP_LINKS.get(habit.habit_type),
        })

    total = len(habit_data)
    completed = sum(1 for h in habit_data if h['done'])
    pct = int(completed / total * 100) if total else 0

    return render_template(
        'index.html',
        user=current_user,
        habit_data=habit_data,
        today=today,
        completed=completed,
        total=total,
        pct=pct,
    )


@habits_bp.route('/habits/new', methods=['GET', 'POST'])
@login_required
def new_habit():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Name is required.', 'danger')
            return redirect('/habits/new')

        habit = Habit(
            user_id    = current_user.id,
            name       = name,
            description= request.form.get('description', '').strip(),
            habit_type = request.form.get('habit_type', 'manual'),
            icon       = request.form.get('icon', '✓').strip() or '✓',
            color      = request.form.get('color', '#4A90E2'),
            sort_order = int(request.form.get('sort_order', 0) or 0),
        )
        db.session.add(habit)
        db.session.commit()
        flash('Habit created.', 'success')
        return redirect('/')

    return render_template('habit_form.html', user=current_user, habit=None)


@habits_bp.route('/habits/quick-add-apps', methods=['POST'])
@login_required
def quick_add_apps():
    """Add the 4 app-linked habits in one click."""
    existing_types = {
        h.habit_type for h in Habit.query.filter_by(user_id=current_user.id).all()
    }
    for i, defaults in enumerate(APP_LINKED_DEFAULTS):
        if defaults['habit_type'] not in existing_types:
            db.session.add(Habit(user_id=current_user.id, sort_order=i, **defaults))
    db.session.commit()
    flash('App habits added.', 'success')
    return redirect('/')


@habits_bp.route('/habits/<int:habit_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_habit(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Name is required.', 'danger')
            return redirect(f'/habits/{habit_id}/edit')

        habit.name        = name
        habit.description = request.form.get('description', '').strip()
        habit.habit_type  = request.form.get('habit_type', habit.habit_type)
        habit.icon        = request.form.get('icon', habit.icon).strip() or habit.icon
        habit.color       = request.form.get('color', habit.color)
        habit.sort_order  = int(request.form.get('sort_order', habit.sort_order) or 0)
        db.session.commit()
        flash('Habit updated.', 'success')
        return redirect('/')

    return render_template('habit_form.html', user=current_user, habit=habit)


@habits_bp.route('/habits/<int:habit_id>/delete', methods=['POST'])
@login_required
def delete_habit(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    action = request.form.get('action', 'archive')
    if action == 'delete':
        db.session.delete(habit)
        flash('Habit deleted.', 'success')
    else:
        habit.active = False
        flash('Habit archived.', 'success')
    db.session.commit()
    return redirect('/')
