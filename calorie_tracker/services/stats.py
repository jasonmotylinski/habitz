from datetime import date, timedelta

from ..models import FoodLog, db


def get_daily_totals(user_id, target_date):
    logs = FoodLog.query.filter_by(
        user_id=user_id,
        logged_date=target_date
    ).all()

    totals = {'calories': 0, 'protein_g': 0, 'carbs_g': 0, 'fat_g': 0}
    for log in logs:
        totals['calories'] += log.calories
        totals['protein_g'] += log.protein_g
        totals['carbs_g'] += log.carbs_g
        totals['fat_g'] += log.fat_g

    return {k: round(v, 1) for k, v in totals.items()}


def get_weekly_summary(user_id, end_date=None):
    if end_date is None:
        end_date = date.today()

    start_date = end_date - timedelta(days=6)
    days = []

    for i in range(7):
        d = start_date + timedelta(days=i)
        totals = get_daily_totals(user_id, d)
        days.append({
            'date': d.isoformat(),
            'day_name': d.strftime('%a'),
            **totals,
        })

    return days
