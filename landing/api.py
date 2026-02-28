import calendar as _cal
from datetime import date, datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from shared import db

from .models import Habit, HabitLog

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/habits/<int:habit_id>/toggle', methods=['POST'])
@login_required
def toggle_habit(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()

    if habit.habit_type != 'manual':
        return jsonify({'error': 'Only manual habits can be toggled'}), 400

    today = date.today()
    log = HabitLog.query.filter_by(habit_id=habit_id, completed_date=today).first()

    if log:
        db.session.delete(log)
        db.session.commit()
        done = False
    else:
        db.session.add(HabitLog(
            habit_id=habit_id,
            user_id=current_user.id,
            completed_date=today,
        ))
        db.session.commit()
        done = True

    return jsonify({'done': done, 'habit_id': habit_id})


@api_bp.route('/habits/calendar')
@login_required
def habits_calendar():
    month_str = request.args.get('month')
    today = date.today()

    if month_str:
        try:
            dt = datetime.strptime(month_str, '%Y-%m')
            year, month = dt.year, dt.month
        except ValueError:
            year, month = today.year, today.month
    else:
        year, month = today.year, today.month

    total = Habit.query.filter_by(user_id=current_user.id, active=True).count()

    last_day = _cal.monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)

    logs = HabitLog.query.filter(
        HabitLog.user_id == current_user.id,
        HabitLog.completed_date >= month_start,
        HabitLog.completed_date <= month_end,
    ).all()

    by_day = {}
    for log in logs:
        d = log.completed_date
        by_day[d] = by_day.get(d, 0) + 1

    days = []
    for d in range(1, last_day + 1):
        day = date(year, month, d)
        completed = by_day.get(day, 0)
        progress = round(min(1.0, completed / total), 4) if total > 0 else 0.0
        days.append({
            'date': day.isoformat(),
            'day': d,
            'weekday': day.weekday(),  # 0=Monday
            'completed': completed,
            'total': total,
            'progress': progress,
            'all_done': total > 0 and completed >= total,
        })

    return jsonify({'year': year, 'month': month, 'days': days})
