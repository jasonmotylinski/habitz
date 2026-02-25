import calendar
from datetime import date, datetime, timedelta

from ..models import Fast

DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def get_daily_progress(user_id, target_hours, date=None):
    """Return daily fasting progress for each day of the current week (Mon-Sun)."""
    if date is None:
        date = datetime.utcnow().date()
    monday = date - timedelta(days=date.weekday())

    days = []
    for i in range(7):
        day = monday + timedelta(days=i)
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)

        fasts = Fast.query.filter(
            Fast.user_id == user_id,
            Fast.started_at >= day_start,
            Fast.started_at < day_end,
            Fast.ended_at.isnot(None),
        ).all()

        hours = sum(f.duration_seconds / 3600 for f in fasts)
        progress = min(1.0, hours / target_hours) if target_hours > 0 else 0.0
        exceeded = hours > target_hours

        days.append({
            'date': day.isoformat(),
            'label': DAY_LABELS[i],
            'hours': round(hours, 1),
            'target': target_hours,
            'progress': round(progress, 4),
            'exceeded': exceeded,
        })

    return days


def get_monthly_progress(user_id, target_hours, year, month):
    """Return daily fasting progress for each day of the given month."""
    month_start = datetime(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    month_end = datetime(year, month, last_day) + timedelta(days=1)

    fasts = Fast.query.filter(
        Fast.user_id == user_id,
        Fast.started_at >= month_start,
        Fast.started_at < month_end,
        Fast.ended_at.isnot(None),
    ).all()

    by_day = {}
    for f in fasts:
        day_key = f.started_at.date()
        by_day.setdefault(day_key, []).append(f)

    days = []
    for d in range(1, last_day + 1):
        day = date(year, month, d)
        day_fasts = by_day.get(day, [])
        hours = sum(f.duration_seconds / 3600 for f in day_fasts)
        progress = min(1.0, hours / target_hours) if target_hours > 0 else 0.0
        exceeded = hours > target_hours

        days.append({
            'date': day.isoformat(),
            'day': d,
            'weekday': day.weekday(),  # 0=Monday … 6=Sunday
            'hours': round(hours, 1),
            'target': target_hours,
            'progress': round(progress, 4),
            'exceeded': exceeded,
        })

    return days
