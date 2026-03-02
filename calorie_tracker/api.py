from datetime import date, datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required


def get_user_today(user):
    tz = ZoneInfo(user.timezone or 'America/New_York')
    return datetime.now(tz).date()

from .models import FoodItem, FoodLog, db
from .services.nutrition import get_or_create_food_item, search_foods
from .services.stats import get_daily_totals, get_weekly_summary

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/foods/search')
@login_required
def food_search():
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    if not query:
        return jsonify({'results': []})

    results = search_foods(query, page)
    return jsonify({'results': results})


@api_bp.route('/foods/<int:food_item_id>')
@login_required
def food_detail(food_item_id):
    item = FoodItem.query.get_or_404(food_item_id)
    return jsonify(item.to_dict())


@api_bp.route('/log', methods=['GET'])
@login_required
def get_logs():
    date_str = request.args.get('date', get_user_today(current_user).isoformat())
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    logs = FoodLog.query.filter_by(
        user_id=current_user.id,
        logged_date=target_date
    ).order_by(FoodLog.logged_at).all()

    return jsonify({
        'date': target_date.isoformat(),
        'entries': [log.to_dict() for log in logs],
        'totals': get_daily_totals(current_user.id, target_date),
        'goals': current_user.to_dict(),
    })


@api_bp.route('/log', methods=['POST'])
@login_required
def create_log():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    food_data = data.get('food_item')
    food_item_id = data.get('food_item_id')

    if food_item_id:
        food_item = FoodItem.query.get(food_item_id)
        if not food_item:
            return jsonify({'error': 'Food item not found'}), 404
    elif food_data:
        food_item = get_or_create_food_item(food_data)
    else:
        return jsonify({'error': 'food_item_id or food_item required'}), 400

    servings = float(data.get('servings', 1.0))
    meal_type = data.get('meal_type', 'snack')
    if meal_type not in ('breakfast', 'lunch', 'dinner', 'snack'):
        return jsonify({'error': 'Invalid meal type'}), 400

    log_date = data.get('date', get_user_today(current_user).isoformat())
    try:
        log_date = date.fromisoformat(log_date)
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    log = FoodLog(
        user_id=current_user.id,
        food_item_id=food_item.id,
        meal_type=meal_type,
        servings=servings,
        logged_date=log_date,
        calories=round(food_item.calories * servings, 1),
        protein_g=round(food_item.protein_g * servings, 1),
        carbs_g=round(food_item.carbs_g * servings, 1),
        fat_g=round(food_item.fat_g * servings, 1),
    )
    db.session.add(log)
    db.session.commit()

    return jsonify(log.to_dict()), 201


@api_bp.route('/log/<int:log_id>', methods=['PUT'])
@login_required
def update_log(log_id):
    log = FoodLog.query.get_or_404(log_id)
    if log.user_id != current_user.id:
        return jsonify({'error': 'Not authorized'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'servings' in data:
        servings = float(data['servings'])
        log.servings = servings
        log.calories = round(log.food_item.calories * servings, 1)
        log.protein_g = round(log.food_item.protein_g * servings, 1)
        log.carbs_g = round(log.food_item.carbs_g * servings, 1)
        log.fat_g = round(log.food_item.fat_g * servings, 1)

    if 'meal_type' in data:
        if data['meal_type'] in ('breakfast', 'lunch', 'dinner', 'snack'):
            log.meal_type = data['meal_type']

    db.session.commit()
    return jsonify(log.to_dict())


@api_bp.route('/log/<int:log_id>', methods=['DELETE'])
@login_required
def delete_log(log_id):
    log = FoodLog.query.get_or_404(log_id)
    if log.user_id != current_user.id:
        return jsonify({'error': 'Not authorized'}), 403

    db.session.delete(log)
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/stats/daily')
@login_required
def daily_stats():
    date_str = request.args.get('date', get_user_today(current_user).isoformat())
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({'error': 'Invalid date'}), 400

    totals = get_daily_totals(current_user.id, target_date)
    return jsonify({
        'date': target_date.isoformat(),
        'totals': totals,
        'goals': current_user.to_dict(),
    })


@api_bp.route('/stats/weekly')
@login_required
def weekly_stats():
    date_str = request.args.get('date', get_user_today(current_user).isoformat())
    try:
        end_date = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({'error': 'Invalid date'}), 400

    days = get_weekly_summary(current_user.id, end_date)
    return jsonify({'days': days})


@api_bp.route('/user/goals', methods=['PUT'])
@login_required
def update_goals():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'daily_calorie_goal' in data:
        current_user.daily_calorie_goal = int(data['daily_calorie_goal'])
    if 'protein_goal_pct' in data:
        current_user.protein_goal_pct = int(data['protein_goal_pct'])
    if 'carb_goal_pct' in data:
        current_user.carb_goal_pct = int(data['carb_goal_pct'])
    if 'fat_goal_pct' in data:
        current_user.fat_goal_pct = int(data['fat_goal_pct'])

    db.session.commit()
    return jsonify(current_user.to_dict())


@api_bp.route('/log/quick', methods=['POST'])
@login_required
def create_quick_log():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        calories = float(data.get('calories', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid calories value'}), 400

    if calories <= 0:
        return jsonify({'error': 'Calories must be greater than 0'}), 400

    name = (data.get('name') or '').strip() or 'Quick Add'
    meal_type = data.get('meal_type', 'snack')
    if meal_type not in ('breakfast', 'lunch', 'dinner', 'snack'):
        return jsonify({'error': 'Invalid meal type'}), 400

    log_date = data.get('date', get_user_today(current_user).isoformat())
    try:
        log_date = date.fromisoformat(log_date)
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    try:
        protein_g = round(float(data.get('protein_g') or 0), 1)
        carbs_g = round(float(data.get('carbs_g') or 0), 1)
        fat_g = round(float(data.get('fat_g') or 0), 1)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid macro value'}), 400

    food_item = FoodItem(
        name=name,
        source='quick_add',
        calories=round(calories, 1),
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
    )
    db.session.add(food_item)
    db.session.flush()

    log = FoodLog(
        user_id=current_user.id,
        food_item_id=food_item.id,
        meal_type=meal_type,
        servings=1,
        logged_date=log_date,
        calories=round(calories, 1),
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
    )
    db.session.add(log)
    db.session.commit()

    return jsonify(log.to_dict()), 201


@api_bp.route('/foods/recent')
@login_required
def recent_foods():
    recent_logs = FoodLog.query.filter_by(
        user_id=current_user.id
    ).order_by(FoodLog.logged_at.desc()).limit(20).all()

    seen = set()
    items = []
    for log in recent_logs:
        if log.food_item_id not in seen and log.food_item.source != 'quick_add':
            seen.add(log.food_item_id)
            items.append(log.food_item.to_dict())
    return jsonify({'items': items})
