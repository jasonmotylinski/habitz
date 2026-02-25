from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
from .models import MealPlan, Meal, db
from .forms import MealPlanForm
from .recipe_importer import import_recipe_from_url, extract_domain_name
import json

planner_bp = Blueprint('planner', __name__, url_prefix='/planner')

def get_week_start(date_obj=None):
    """Get the Monday of the week for a given date"""
    if date_obj is None:
        date_obj = date.today()
    return date_obj - timedelta(days=date_obj.weekday())

def get_week_dates(week_start):
    """Get all dates for a week starting from Monday"""
    return [week_start + timedelta(days=i) for i in range(7)]

@planner_bp.route('/')
@login_required
def index():
    """View weekly meal plan"""
    if not current_user.household:
        return redirect(url_for('household.create'))

    week_param = request.args.get('week', type=str)

    if week_param:
        try:
            week_start = datetime.strptime(week_param, '%Y-%m-%d').date()
        except ValueError:
            week_start = get_week_start()
    else:
        week_start = get_week_start()

    week_dates = get_week_dates(week_start)
    meal_types = ['dinner']  # UI only shows dinner, but backend supports all types

    # Get meal plans for the week (from household)
    meal_plans = {}
    for day in week_dates:
        meal_plans[day] = {}
        for meal_type in meal_types:
            plan = MealPlan.query.filter_by(
                household_id=current_user.household_id,
                date=day,
                meal_type=meal_type
            ).first()
            meal_plans[day][meal_type] = plan

    # Get next and previous week
    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    return render_template('planner/index.html',
                         week_start=week_start,
                         week_dates=week_dates,
                         meal_types=meal_types,
                         meal_plans=meal_plans,
                         prev_week=prev_week,
                         next_week=next_week,
                         today=date.today())

@planner_bp.route('/<date_str>/<meal_type>', methods=['GET', 'POST'])
@login_required
def set_meal(date_str, meal_type):
    """Set meal for a specific day and meal type"""
    if not current_user.household:
        return redirect(url_for('household.create'))

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        flash('Invalid date', 'danger')
        return redirect(url_for('planner.index'))

    # Check if meal_id is passed as query parameter (quick add from recipe view)
    quick_meal_id = request.args.get('meal_id', type=int)

    if meal_type not in ['breakfast', 'lunch', 'dinner']:
        flash('Invalid meal type', 'danger')
        return redirect(url_for('planner.index'))

    # Handle quick add from recipe view
    if quick_meal_id:
        meal_plan = MealPlan.query.filter_by(
            household_id=current_user.household_id,
            date=target_date,
            meal_type=meal_type
        ).first()

        if not meal_plan:
            meal_plan = MealPlan(
                household_id=current_user.household_id,
                date=target_date,
                meal_type=meal_type
            )

        meal_plan.meal_id = quick_meal_id
        meal_plan.custom_entry = None
        db.session.add(meal_plan)
        db.session.commit()
        flash('Meal added to your plan!', 'success')
        week_start = get_week_start(target_date)
        return redirect(url_for('planner.index', week=week_start.isoformat()))

    form = MealPlanForm()

    # Populate meal choices
    meals = Meal.query.order_by(Meal.name).all()
    form.meal_id.choices = [(0, '-- None --')] + [(m.id, m.name) for m in meals]

    if form.validate_on_submit():
        # Get or create meal plan entry (from household)
        meal_plan = MealPlan.query.filter_by(
            household_id=current_user.household_id,
            date=target_date,
            meal_type=meal_type
        ).first()

        if not meal_plan:
            meal_plan = MealPlan(
                household_id=current_user.household_id,
                date=target_date,
                meal_type=meal_type
            )

        # PRIMARY: Handle URL import
        url_input = request.form.get('url', '').strip()

        if url_input:
            try:
                # Try fast schema.org parsing first (instant)
                recipe_data = import_recipe_from_url(url_input)

                if recipe_data:
                    # SUCCESS: Schema.org data found, create Meal immediately
                    meal = Meal(
                        name=recipe_data['name'],
                        description=recipe_data.get('description', ''),
                        category=recipe_data.get('category'),
                        ingredients=recipe_data['ingredients'],
                        instructions=recipe_data['instructions'],
                        image_filename=recipe_data.get('image_url'),
                        source_url=url_input,
                        source_name=extract_domain_name(url_input),
                        household_id=current_user.household_id,
                        created_by=current_user.id
                    )
                    db.session.add(meal)
                    db.session.flush()  # Get meal.id

                    meal_plan.meal_id = meal.id
                    meal_plan.source_url = url_input
                    meal_plan.import_status = 'imported'
                    meal_plan.custom_entry = None
                    db.session.add(meal_plan)
                    db.session.commit()
                    flash(f'✓ Recipe "{meal.name}" imported and added to {meal_type.title()}', 'success')
                else:
                    # No schema.org data: Queue for async Claude processing
                    domain = extract_domain_name(url_input)
                    meal_plan.source_url = url_input
                    meal_plan.import_status = 'pending'  # Cron job will process this
                    meal_plan.meal_id = None
                    meal_plan.custom_entry = f"Recipe from {domain}"
                    db.session.add(meal_plan)
                    db.session.commit()
                    flash(f'⏳ Recipe from {domain} saved! Details will be imported shortly...', 'info')

            except Exception as e:
                # NETWORK/HTTP ERROR: Queue for async retry
                meal_plan.source_url = url_input
                meal_plan.import_status = 'pending'  # Cron job will retry
                meal_plan.meal_id = None
                meal_plan.custom_entry = 'Recipe from URL'
                db.session.add(meal_plan)
                db.session.commit()
                flash('⏳ Saved URL for later processing. Will retry shortly...', 'info')

        # SECONDARY: Set either meal or custom entry
        elif form.meal_id.data and form.meal_id.data != 0:
            meal_plan.meal_id = form.meal_id.data
            meal_plan.custom_entry = None
            meal_plan.source_url = None
            db.session.add(meal_plan)
            db.session.commit()
            flash('Meal updated successfully!', 'success')
        elif form.custom_entry.data:
            meal_plan.meal_id = None
            meal_plan.custom_entry = form.custom_entry.data
            meal_plan.source_url = None
            db.session.add(meal_plan)
            db.session.commit()
            flash('Meal updated successfully!', 'success')
        else:
            # Delete if neither meal nor custom entry nor URL
            if meal_plan.id:
                db.session.delete(meal_plan)
            db.session.commit()
            flash('Meal removed', 'info')
            return redirect(request.referrer or url_for('planner.index'))

        # Get the week start for the target date
        week_start = get_week_start(target_date)
        return redirect(url_for('planner.index', week=week_start.isoformat()))

    # Pre-fill form
    existing = MealPlan.query.filter_by(
        household_id=current_user.household_id,
        date=target_date,
        meal_type=meal_type
    ).first()

    if existing:
        if existing.meal_id:
            form.meal_id.data = existing.meal_id
        else:
            form.custom_entry.data = existing.custom_entry

    # Get recent meals for quick access
    recent_meals = Meal.query.order_by(Meal.created_at.desc()).limit(6).all()

    return render_template('planner/set_meal.html',
                         form=form,
                         date=target_date,
                         meal_type=meal_type,
                         recent_meals=recent_meals)

@planner_bp.route('/<date_str>/<meal_type>/delete', methods=['POST'])
@login_required
def delete_meal(date_str, meal_type):
    """Delete meal from plan"""
    if not current_user.household:
        return redirect(url_for('household.create'))

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date'}), 400

    meal_plan = MealPlan.query.filter_by(
        household_id=current_user.household_id,
        date=target_date,
        meal_type=meal_type
    ).first()

    if meal_plan:
        db.session.delete(meal_plan)
        db.session.commit()
        flash('Meal removed', 'info')

    return redirect(request.referrer or url_for('planner.index'))

@planner_bp.route('/search', methods=['GET'])
@login_required
def search_meals():
    """Search meals by query string"""
    query = request.args.get('q', '').strip()

    if not query or len(query) < 2:
        return jsonify([])

    # Search in meal name and description
    meals = Meal.query.filter(
        (Meal.name.ilike(f'%{query}%')) | (Meal.description.ilike(f'%{query}%'))
    ).limit(10).all()

    return jsonify([{
        'id': meal.id,
        'name': meal.name,
        'category': meal.category or 'Uncategorized'
    } for meal in meals])
