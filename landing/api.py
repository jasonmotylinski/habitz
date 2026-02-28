from datetime import date

from flask import Blueprint, jsonify
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
