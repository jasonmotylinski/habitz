import calendar
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func

from .models import Fast, MicroFast, db
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


@api_bp.route('/fast/<int:fast_id>', methods=['PATCH'])
@login_required
def update_fast(fast_id):
    fast = Fast.query.filter_by(id=fast_id, user_id=current_user.id).first()
    if not fast:
        return jsonify({'error': 'Fast not found'}), 404
    if fast.is_active:
        return jsonify({'error': 'Cannot edit an active fast. Stop it first.'}), 400

    data = request.get_json(silent=True) or {}
    errors = []

    # Update started_at if provided
    if 'started_at' in data:
        try:
            new_start = datetime.fromisoformat(data['started_at'].replace('Z', '+00:00'))
            if new_start.tzinfo is not None:
                new_start = new_start.replace(tzinfo=None)
            fast.started_at = new_start
        except (ValueError, AttributeError):
            errors.append('Invalid started_at format')

    # Update ended_at if provided
    if 'ended_at' in data:
        try:
            new_end = datetime.fromisoformat(data['ended_at'].replace('Z', '+00:00'))
            if new_end.tzinfo is not None:
                new_end = new_end.replace(tzinfo=None)
            fast.ended_at = new_end
        except (ValueError, AttributeError):
            errors.append('Invalid ended_at format')

    # Update target_hours if provided
    if 'target_hours' in data:
        try:
            fast.target_hours = max(1, min(72, int(data['target_hours'])))
        except (ValueError, TypeError):
            errors.append('Invalid target_hours')

    # Update completed status
    if 'completed' in data:
        fast.completed = bool(data['completed'])

    # Update note if provided
    if 'note' in data:
        fast.note = data['note']

    if errors:
        return jsonify({'error': '; '.join(errors)}), 400

    try:
        db.session.commit()
        return jsonify(fast.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


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


# ── Micro Fast endpoints ──────────────────────────────────────────────────────

@api_bp.route('/micro/start', methods=['POST'])
@login_required
def start_micro_fast():
    active = MicroFast.query.filter_by(user_id=current_user.id, ended_at=None).first()
    if active:
        return jsonify({'error': 'A micro fast is already active'}), 400

    data = request.get_json(silent=True) or {}
    target_minutes = data.get('target_minutes', current_user.default_micro_fast_minutes or 180)
    label = data.get('label')

    mf = MicroFast(
        user_id=current_user.id,
        target_minutes=max(1, int(target_minutes)),
        label=label,
        started_at=datetime.utcnow(),
    )
    db.session.add(mf)
    db.session.commit()
    return jsonify(mf.to_dict()), 201


@api_bp.route('/micro/stop', methods=['POST'])
@login_required
def stop_micro_fast():
    active = MicroFast.query.filter_by(user_id=current_user.id, ended_at=None).first()
    if not active:
        return jsonify({'error': 'No active micro fast'}), 400

    active.ended_at = datetime.utcnow()
    active.completed = active.duration_seconds >= active.target_seconds
    db.session.commit()
    return jsonify(active.to_dict())


@api_bp.route('/micro/active')
@login_required
def active_micro_fast():
    active = MicroFast.query.filter_by(user_id=current_user.id, ended_at=None).first()
    if not active:
        return jsonify(None)
    return jsonify(active.to_dict())


@api_bp.route('/micro/today')
@login_required
def micro_fast_today():
    from zoneinfo import ZoneInfo
    from datetime import timezone as dt_timezone
    tz = ZoneInfo(current_user.timezone or 'America/New_York')
    now_local = datetime.now(dt_timezone.utc).astimezone(tz)
    today_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end_local = now_local.replace(hour=23, minute=59, second=59, microsecond=999999)
    today_start_utc = today_start_local.astimezone(dt_timezone.utc).replace(tzinfo=None)
    today_end_utc = today_end_local.astimezone(dt_timezone.utc).replace(tzinfo=None)

    records = MicroFast.query.filter(
        MicroFast.user_id == current_user.id,
        MicroFast.started_at >= today_start_utc,
        MicroFast.started_at <= today_end_utc,
    ).order_by(MicroFast.started_at.asc()).all()

    return jsonify([mf.to_dict() for mf in records])


@api_bp.route('/micro/<int:mf_id>', methods=['PATCH'])
@login_required
def update_micro_fast(mf_id):
    mf = MicroFast.query.filter_by(id=mf_id, user_id=current_user.id).first()
    if not mf:
        return jsonify({'error': 'Micro fast not found'}), 404
    if mf.is_active:
        return jsonify({'error': 'Cannot edit an active micro fast. Stop it first.'}), 400

    data = request.get_json(silent=True) or {}
    errors = []

    if 'started_at' in data:
        try:
            new_start = datetime.fromisoformat(data['started_at'].replace('Z', '+00:00'))
            if new_start.tzinfo is not None:
                new_start = new_start.replace(tzinfo=None)
            mf.started_at = new_start
        except (ValueError, AttributeError):
            errors.append('Invalid started_at format')

    if 'ended_at' in data:
        try:
            new_end = datetime.fromisoformat(data['ended_at'].replace('Z', '+00:00'))
            if new_end.tzinfo is not None:
                new_end = new_end.replace(tzinfo=None)
            mf.ended_at = new_end
        except (ValueError, AttributeError):
            errors.append('Invalid ended_at format')

    if 'target_minutes' in data:
        try:
            mf.target_minutes = max(1, min(360, int(data['target_minutes'])))
        except (ValueError, TypeError):
            errors.append('Invalid target_minutes')

    if 'completed' in data:
        mf.completed = bool(data['completed'])

    if 'label' in data:
        mf.label = data['label']

    if 'note' in data:
        mf.note = data['note']

    if errors:
        return jsonify({'error': '; '.join(errors)}), 400

    try:
        db.session.commit()
        return jsonify(mf.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@api_bp.route('/micro/<int:mf_id>', methods=['DELETE'])
@login_required
def delete_micro_fast(mf_id):
    mf = MicroFast.query.filter_by(id=mf_id, user_id=current_user.id).first()
    if not mf:
        return jsonify({'error': 'Micro fast not found'}), 404
    if mf.is_active:
        return jsonify({'error': 'Cannot delete an active micro fast. Stop it first.'}), 400

    db.session.delete(mf)
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/user/micro-goal', methods=['PUT'])
@login_required
def update_micro_goal():
    data = request.get_json(silent=True) or {}
    if 'default_micro_fast_minutes' in data:
        try:
            minutes = max(30, min(360, int(data['default_micro_fast_minutes'])))
            current_user.default_micro_fast_minutes = minutes
            db.session.commit()
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid default_micro_fast_minutes'}), 400
    return jsonify(current_user.to_dict())
