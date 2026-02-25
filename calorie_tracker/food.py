from flask import Blueprint, render_template, request
from flask_login import login_required

food_bp = Blueprint('food', __name__, url_prefix='/food')


@food_bp.route('/search')
@login_required
def search():
    meal_type = request.args.get('meal', 'snack')
    date_str = request.args.get('date', '')
    return render_template('food/search.html', meal_type=meal_type, date=date_str)


@food_bp.route('/log/<int:food_item_id>')
@login_required
def log(food_item_id):
    meal_type = request.args.get('meal', 'snack')
    date_str = request.args.get('date', '')
    return render_template('food/log.html',
                           food_item_id=food_item_id,
                           meal_type=meal_type,
                           date=date_str)


@food_bp.route('/quick-add')
@login_required
def quick_add():
    meal_type = request.args.get('meal', 'snack')
    date_str = request.args.get('date', '')
    return render_template('food/quick_add.html', meal_type=meal_type, date=date_str)
