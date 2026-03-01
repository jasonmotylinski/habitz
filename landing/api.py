import calendar as _cal
from datetime import date, datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from shared import db

from .models import Habit, HabitLog, DailyNote, DailyMood


def get_user_today(user):
    """Get today's date in the user's timezone."""
    tz = ZoneInfo(user.timezone or 'America/New_York')
    return datetime.now(tz).date()

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/habits/<int:habit_id>/toggle', methods=['POST'])
@login_required
def toggle_habit(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()

    if habit.habit_type != 'manual':
        return jsonify({'error': 'Only manual habits can be toggled'}), 400

    date_str = request.args.get('date')
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            target_date = get_user_today(current_user)
    else:
        target_date = get_user_today(current_user)

    log = HabitLog.query.filter_by(habit_id=habit_id, completed_date=target_date).first()

    if log:
        db.session.delete(log)
        db.session.commit()
        done = False
    else:
        db.session.add(HabitLog(
            habit_id=habit_id,
            user_id=current_user.id,
            completed_date=target_date,
        ))
        db.session.commit()
        done = True

    return jsonify({'done': done, 'habit_id': habit_id})


@api_bp.route('/habits/calendar')
@login_required
def habits_calendar():
    month_str = request.args.get('month')
    today = get_user_today(current_user)

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


@api_bp.route('/habits/weekly')
@login_required
def habits_weekly():
    today = get_user_today(current_user)
    # Get the last 7 days (including today)
    start_date = today - timedelta(days=6)

    total = Habit.query.filter_by(user_id=current_user.id, active=True).count()

    logs = HabitLog.query.filter(
        HabitLog.user_id == current_user.id,
        HabitLog.completed_date >= start_date,
        HabitLog.completed_date <= today,
    ).all()

    by_day = {}
    for log in logs:
        d = log.completed_date
        by_day[d] = by_day.get(d, 0) + 1

    days = []
    day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for i in range(7):
        day = start_date + timedelta(days=i)
        completed = by_day.get(day, 0)
        progress = round(min(1.0, completed / total), 4) if total > 0 else 0.0
        day_label = day_labels[day.weekday()]
        days.append({
            'date': day.isoformat(),
            'label': day_label,
            'completed': completed,
            'total': total,
            'progress': progress,
            'is_today': day == today,
        })

    return jsonify({'days': days})


@api_bp.route('/daily/note', methods=['GET'])
@login_required
def get_daily_note():
    """Get daily note for a specific date"""
    date_str = request.args.get('date')
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        target_date = get_user_today(current_user)

    note = DailyNote.query.filter_by(
        user_id=current_user.id,
        date=target_date
    ).first()

    return jsonify(note.to_dict() if note else {'date': target_date.isoformat(), 'content': None})


@api_bp.route('/daily/note', methods=['POST'])
@login_required
def create_or_update_note():
    """Create or update daily note"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    date_str = data.get('date')
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        target_date = get_user_today(current_user)

    content = data.get('content', '').strip()

    note = DailyNote.query.filter_by(
        user_id=current_user.id,
        date=target_date
    ).first()

    if note:
        note.content = content
        db.session.commit()
    else:
        note = DailyNote(
            user_id=current_user.id,
            date=target_date,
            content=content
        )
        db.session.add(note)
        db.session.commit()

    return jsonify(note.to_dict()), 201 if not note else 200


@api_bp.route('/daily/mood', methods=['GET'])
@login_required
def get_daily_mood():
    """Get daily mood for a specific date"""
    date_str = request.args.get('date')
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        target_date = get_user_today(current_user)

    mood = DailyMood.query.filter_by(
        user_id=current_user.id,
        date=target_date
    ).first()

    return jsonify(mood.to_dict() if mood else {'date': target_date.isoformat(), 'mood': None})


@api_bp.route('/daily/mood', methods=['POST'])
@login_required
def create_or_update_mood():
    """Create or update daily mood"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    date_str = data.get('date')
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        target_date = get_user_today(current_user)

    mood_value = data.get('mood')
    if mood_value is None:
        return jsonify({'error': 'Mood value required'}), 400

    try:
        mood_value = int(mood_value)
        if mood_value < 1 or mood_value > 5:
            return jsonify({'error': 'Mood must be between 1 and 5'}), 400
    except (TypeError, ValueError):
        return jsonify({'error': 'Mood must be an integer'}), 400

    notes = data.get('notes', '').strip()
    emoji = data.get('emoji')

    mood = DailyMood.query.filter_by(
        user_id=current_user.id,
        date=target_date
    ).first()

    if mood:
        mood.mood = mood_value
        mood.emoji = emoji
        mood.notes = notes
        db.session.commit()
    else:
        mood = DailyMood(
            user_id=current_user.id,
            date=target_date,
            mood=mood_value,
            emoji=emoji,
            notes=notes
        )
        db.session.add(mood)
        db.session.commit()

    return jsonify(mood.to_dict()), 201


@api_bp.route('/daily/summary')
@login_required
def get_daily_summary():
    """Get daily summary (habits, note, mood) for a specific date"""
    date_str = request.args.get('date')
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        target_date = get_user_today(current_user)

    # Get habits for the day
    logs = HabitLog.query.filter_by(
        user_id=current_user.id,
        completed_date=target_date
    ).all()

    habit_ids = set(log.habit_id for log in logs)
    total_habits = Habit.query.filter_by(user_id=current_user.id, active=True).count()
    completed_habits = len(habit_ids)

    # Get note
    note = DailyNote.query.filter_by(
        user_id=current_user.id,
        date=target_date
    ).first()

    # Get mood
    mood = DailyMood.query.filter_by(
        user_id=current_user.id,
        date=target_date
    ).first()

    return jsonify({
        'date': target_date.isoformat(),
        'habits': {
            'completed': completed_habits,
            'total': total_habits,
            'progress': round(completed_habits / total_habits, 2) if total_habits > 0 else 0,
        },
        'note': note.to_dict() if note else None,
        'mood': mood.to_dict() if mood else None,
    })
