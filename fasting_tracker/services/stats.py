import calendar
from datetime import date, datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from ..models import Fast

DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def _local_end_date(fast, tz):
    """Return the local calendar date when a fast ended."""
    return fast.ended_at.replace(tzinfo=timezone.utc).astimezone(tz).date()


def _day_utc_bounds(day, tz):
    """Return (start_utc, end_utc) as naive UTC datetimes for `day` in user's tz."""
    local_start = datetime(day.year, day.month, day.day, tzinfo=tz)
    next_day = day + timedelta(days=1)
    local_end = datetime(next_day.year, next_day.month, next_day.day, tzinfo=tz)
    start_utc = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = local_end.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def get_daily_progress(user_id, target_hours, date=None, user_timezone='UTC'):
    """Return daily fasting progress for each day of the current week (Mon-Sun).

    A fast is attributed entirely to the local day it ended, not split across days.
    """
    tz = ZoneInfo(user_timezone or 'UTC')

    if date is None:
        date = datetime.now(tz).date()
    monday = date - timedelta(days=date.weekday())
    sunday = monday + timedelta(days=6)

    # Fetch fasts that ended within the week's UTC span.
    week_start_utc, _ = _day_utc_bounds(monday, tz)
    _, week_end_utc = _day_utc_bounds(sunday, tz)
    fasts = Fast.query.filter(
        Fast.user_id == user_id,
        Fast.ended_at >= week_start_utc,
        Fast.ended_at < week_end_utc,
        Fast.ended_at.isnot(None),
    ).all()

    days = []
    for i in range(7):
        day = monday + timedelta(days=i)
        hours = sum(
            f.duration_seconds / 3600
            for f in fasts
            if _local_end_date(f, tz) == day
        )
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


def get_monthly_progress(user_id, target_hours, year, month, user_timezone='UTC'):
    """Return daily fasting progress for each day of the given month.

    A fast is attributed entirely to the local day it ended, not split across days.
    """
    tz = ZoneInfo(user_timezone or 'UTC')

    last_day = calendar.monthrange(year, month)[1]

    # Fetch fasts that ended within the month's UTC span.
    month_start_utc, _ = _day_utc_bounds(date(year, month, 1), tz)
    _, month_end_utc = _day_utc_bounds(date(year, month, last_day), tz)
    fasts = Fast.query.filter(
        Fast.user_id == user_id,
        Fast.ended_at >= month_start_utc,
        Fast.ended_at < month_end_utc,
        Fast.ended_at.isnot(None),
    ).all()

    days = []
    for d in range(1, last_day + 1):
        day = date(year, month, d)
        hours = sum(
            f.duration_seconds / 3600
            for f in fasts
            if _local_end_date(f, tz) == day
        )
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
