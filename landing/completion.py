from datetime import date, timedelta

from sqlalchemy import func

from shared import db

from .models import HabitLog


def check_completion(habit, user, today: date) -> bool:
    """Return True if habit is completed for today."""
    if habit.habit_type == 'manual':
        return HabitLog.query.filter_by(
            habit_id=habit.id, completed_date=today).first() is not None

    elif habit.habit_type == 'calories':
        from calorie_tracker.models import FoodLog
        total = db.session.query(func.sum(FoodLog.calories)).filter(
            FoodLog.user_id == user.id,
            FoodLog.logged_date == today,
        ).scalar() or 0
        return total >= (user.daily_calorie_goal or 0) and (user.daily_calorie_goal or 0) > 0

    elif habit.habit_type == 'workout':
        from workout_tracker.models import WorkoutLog
        return db.session.query(WorkoutLog).filter(
            WorkoutLog.user_id == user.id,
            WorkoutLog.completed_at.isnot(None),
            func.date(WorkoutLog.completed_at) == today,
        ).first() is not None

    elif habit.habit_type == 'fasting':
        from fasting_tracker.models import Fast
        return db.session.query(Fast).filter(
            Fast.user_id == user.id,
            Fast.completed == True,
            func.date(Fast.ended_at) == today,
        ).first() is not None

    elif habit.habit_type == 'meals':
        if not user.household_id:
            return False
        from meal_planner.models import MealPlan
        return db.session.query(MealPlan).filter(
            MealPlan.household_id == user.household_id,
            MealPlan.date == today,
        ).first() is not None

    return False


def sync_app_linked(habit, user, today: date):
    """Write a HabitLog row for app-linked habits that completed today."""
    if habit.habit_type == 'manual':
        return
    if check_completion(habit, user, today):
        exists = HabitLog.query.filter_by(
            habit_id=habit.id, completed_date=today).first()
        if not exists:
            db.session.add(HabitLog(
                habit_id=habit.id,
                user_id=user.id,
                completed_date=today,
            ))
            db.session.commit()
    else:
        # Remove any stale log if activity was deleted today
        stale = HabitLog.query.filter_by(
            habit_id=habit.id, completed_date=today).first()
        if stale:
            db.session.delete(stale)
            db.session.commit()


def current_streak(habit_id: int) -> int:
    """Count consecutive days ending today (or yesterday) with a HabitLog."""
    logs = (
        HabitLog.query
        .filter_by(habit_id=habit_id)
        .order_by(HabitLog.completed_date.desc())
        .all()
    )
    if not logs:
        return 0

    log_dates = {log.completed_date for log in logs}
    today = date.today()
    streak = 0
    cursor = today

    # If today isn't done yet, start checking from yesterday
    if cursor not in log_dates:
        cursor = today - timedelta(days=1)

    while cursor in log_dates:
        streak += 1
        cursor -= timedelta(days=1)

    return streak
