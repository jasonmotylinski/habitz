import calendar
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from .models import Fast, db
from .services.stats import get_daily_progress, get_monthly_progress

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/fast/start', methods=['POST'])
@login_required
def start_fast():
    active = Fast.query.filter_by(user_id=current_user.id, ended_at=None).first()
    if active:
        return jsonify({'error': 'A fast is already active'}), 400

    data = request.get_json(silent=True) or {}
    target_hours = data.get('target_hours', current_user.default_fast_hours)

    fast = Fast(
        user_id=current_user.id,
        target_hours=target_hours,
        started_at=datetime.utcnow(),
    )
    db.session.add(fast)
    db.session.commit()
    return jsonify(fast.to_dict()), 201


@api_bp.route('/fast/stop', methods=['POST'])
@login_required
def stop_fast():
    active = Fast.query.filter_by(user_id=current_user.id, ended_at=None).first()
    if not active:
        return jsonify({'error': 'No active fast'}), 400

    active.ended_at = datetime.utcnow()
    active.completed = active.duration_seconds >= active.target_seconds
    db.session.commit()
    return jsonify(active.to_dict())


@api_bp.route('/fast/active')
@login_required
def active_fast():
    active = Fast.query.filter_by(user_id=current_user.id, ended_at=None).first()
    if not active:
        return jsonify(None)
    return jsonify(active.to_dict())


@api_bp.route('/fast/active', methods=['PATCH'])
@login_required
def update_active_fast():
    active = Fast.query.filter_by(user_id=current_user.id, ended_at=None).first()
    if not active:
        return jsonify({'error': 'No active fast'}), 400

    data = request.get_json(silent=True) or {}
    if 'started_at' not in data:
        return jsonify({'error': 'started_at is required'}), 400

    try:
        new_start = datetime.fromisoformat(data['started_at'].replace('Z', '+00:00'))
        if new_start.tzinfo is not None:
            new_start = new_start.replace(tzinfo=None)
    except (ValueError, AttributeError):
        return jsonify({'error': 'Invalid started_at format'}), 400

    now = datetime.utcnow()
    if new_start >= now:
        return jsonify({'error': 'Start time must be in the past'}), 400
    if (now - new_start).days > 7:
        return jsonify({'error': 'Start time cannot be more than 7 days ago'}), 400

    active.started_at = new_start
    db.session.commit()
    return jsonify(active.to_dict())


@api_bp.route('/fast/history')
@login_required
def fast_history():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    month_str = request.args.get('month')

    query = Fast.query.filter(
        Fast.user_id == current_user.id,
        Fast.ended_at.isnot(None),
    )

    if month_str:
        try:
            dt = datetime.strptime(month_str, '%Y-%m')
            month_start = datetime(dt.year, dt.month, 1)
            last_day = calendar.monthrange(dt.year, dt.month)[1]
            month_end = datetime(dt.year, dt.month, last_day) + timedelta(days=1)
            query = query.filter(
                Fast.started_at >= month_start,
                Fast.started_at < month_end,
            )
        except ValueError:
            pass

    pagination = query.order_by(Fast.started_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'fasts': [f.to_dict() for f in pagination.items],
        'page': pagination.page,
        'total_pages': pagination.pages,
        'total': pagination.total,
    })


@api_bp.route('/fast/<int:fast_id>', methods=['DELETE'])
@login_required
def delete_fast(fast_id):
    fast = Fast.query.filter_by(id=fast_id, user_id=current_user.id).first()
    if not fast:
        return jsonify({'error': 'Fast not found'}), 404
    if fast.is_active:
        return jsonify({'error': 'Cannot delete an active fast. Stop it first.'}), 400

    db.session.delete(fast)
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/stats/weekly')
@login_required
def weekly_stats():
    date_str = request.args.get('date')
    date = None
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    days = get_daily_progress(
        current_user.id, current_user.default_fast_hours, date,
        user_timezone=current_user.timezone or 'UTC',
    )
    return jsonify({'days': days})


@api_bp.route('/stats/monthly')
@login_required
def monthly_stats():
    month_str = request.args.get('month')
    if month_str:
        try:
            dt = datetime.strptime(month_str, '%Y-%m')
            year, month = dt.year, dt.month
        except ValueError:
            now = datetime.utcnow()
            year, month = now.year, now.month
    else:
        now = datetime.utcnow()
        year, month = now.year, now.month

    days = get_monthly_progress(
        current_user.id, current_user.default_fast_hours, year, month,
        user_timezone=current_user.timezone or 'UTC',
    )
    return jsonify({'year': year, 'month': month, 'days': days})


@api_bp.route('/user/goals', methods=['PUT'])
@login_required
def update_goals():
    data = request.get_json(silent=True) or {}
    if 'default_fast_hours' in data:
        current_user.default_fast_hours = max(1, min(72, int(data['default_fast_hours'])))
    db.session.commit()
    return jsonify(current_user.to_dict())
