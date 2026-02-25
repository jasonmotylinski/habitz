from datetime import date, timedelta

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .forms import GoalsForm
from .models import FoodLog, db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('home.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    date_str = request.args.get('date')
    if date_str:
        try:
            view_date = date.fromisoformat(date_str)
        except ValueError:
            view_date = date.today()
    else:
        view_date = date.today()

    prev_date = view_date - timedelta(days=1)
    next_date = view_date + timedelta(days=1)

    logs = FoodLog.query.filter_by(
        user_id=current_user.id,
        logged_date=view_date
    ).order_by(FoodLog.logged_at).all()

    meals = {
        'breakfast': [],
        'lunch': [],
        'dinner': [],
        'snack': [],
    }
    totals = {'calories': 0, 'protein_g': 0, 'carbs_g': 0, 'fat_g': 0}

    for log in logs:
        meals[log.meal_type].append(log)
        totals['calories'] += log.calories
        totals['protein_g'] += log.protein_g
        totals['carbs_g'] += log.carbs_g
        totals['fat_g'] += log.fat_g

    meal_totals = {}
    for meal_type, entries in meals.items():
        meal_totals[meal_type] = sum(e.calories for e in entries)

    # Weekly data
    week_start = view_date - timedelta(days=view_date.weekday())
    weekly = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        day_cals = db.session.query(
            db.func.coalesce(db.func.sum(FoodLog.calories), 0)
        ).filter_by(user_id=current_user.id, logged_date=d).scalar()
        weekly.append({
            'date': d,
            'day': d.strftime('%a')[0],
            'calories': round(day_cals),
            'is_today': d == view_date,
        })

    return render_template('dashboard.html',
                           view_date=view_date,
                           prev_date=prev_date,
                           next_date=next_date,
                           meals=meals,
                           meal_totals=meal_totals,
                           totals=totals,
                           weekly=weekly)


@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = GoalsForm(obj=current_user)
    if form.validate_on_submit():
        current_user.daily_calorie_goal = form.daily_calorie_goal.data
        current_user.protein_goal_pct = form.protein_goal_pct.data
        current_user.carb_goal_pct = form.carb_goal_pct.data
        current_user.fat_goal_pct = form.fat_goal_pct.data
        db.session.commit()
        from flask import flash
        flash('Goals updated!', 'success')
        return redirect(url_for('main.settings'))

    return render_template('settings.html', form=form)
