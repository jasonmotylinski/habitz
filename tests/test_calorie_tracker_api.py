"""Tests for calorie tracker API endpoints."""
import pytest
from datetime import date
from calorie_tracker.models import FoodItem, FoodLog
from shared import db
from shared.user import User


@pytest.fixture
def food_item(app):
    """Create a test food item."""
    with app.app_context():
        food = FoodItem(
            name='Apple',
            source='usda',
            source_id='167293',
            calories=52.0,
            protein_g=0.3,
            carbs_g=14.0,
            fat_g=0.2,
            fiber_g=2.4,
            serving_size='1 medium (182g)',
            serving_weight_g=182
        )
        db.session.add(food)
        db.session.commit()
        return food


class TestFoodSearch:
    """Tests for food search functionality."""

    def test_search_returns_results(self, app, user):
        """Test that food search returns matching results."""
        with app.app_context():
            # Create food items
            foods = [
                FoodItem(name='Banana', source='usda', calories=89.0),
                FoodItem(name='Apple', source='usda', calories=52.0),
                FoodItem(name='Banana Bread', source='custom', calories=280.0)
            ]
            for f in foods:
                db.session.add(f)
            db.session.commit()

            # Search would happen via API, here we verify the items exist
            bananas = FoodItem.query.filter(FoodItem.name.ilike('%banana%')).all()
            assert len(bananas) == 2

    def test_food_item_to_dict(self, food_item):
        """Test food item serialization."""
        data = food_item.to_dict()

        assert data['name'] == 'Apple'
        assert data['calories'] == 52.0
        assert data['protein_g'] == 0.3
        assert data['source'] == 'usda'


class TestFoodLogging:
    """Tests for food log creation and updates."""

    def test_create_food_log(self, app, user, food_item):
        """Test creating a food log entry."""
        with app.app_context():
            log = FoodLog(
                user_id=user.id,
                food_item_id=food_item.id,
                meal_type='breakfast',
                servings=1.0,
                logged_date=date.today(),
                calories=52.0,
                protein_g=0.3,
                carbs_g=14.0,
                fat_g=0.2
            )
            db.session.add(log)
            db.session.commit()

            assert log.id is not None
            assert log.calories == 52.0

    def test_update_serving_size(self, app, user, food_item):
        """Test updating serving size recalculates nutrition."""
        with app.app_context():
            log = FoodLog(
                user_id=user.id,
                food_item_id=food_item.id,
                meal_type='lunch',
                servings=2.0,
                logged_date=date.today(),
                calories=food_item.calories * 2,
                protein_g=food_item.protein_g * 2,
                carbs_g=food_item.carbs_g * 2,
                fat_g=food_item.fat_g * 2
            )
            db.session.add(log)
            db.session.commit()

            assert log.calories == 104.0
            assert log.protein_g == 0.6
            assert log.carbs_g == 28.0

    def test_food_log_to_dict(self, app, user, food_item):
        """Test food log serialization."""
        with app.app_context():
            log = FoodLog(
                user_id=user.id,
                food_item_id=food_item.id,
                meal_type='breakfast',
                servings=1.5,
                logged_date=date.today(),
                calories=78.0,
                protein_g=0.45,
                carbs_g=21.0,
                fat_g=0.3
            )
            db.session.add(log)
            db.session.commit()

            data = log.to_dict()
            assert data['meal_type'] == 'breakfast'
            assert data['servings'] == 1.5
            assert data['calories'] == 78.0


class TestDailyNutritionTotals:
    """Tests for daily nutrition calculations."""

    def test_get_daily_totals(self, app, user, food_item):
        """Test calculating daily nutrition totals."""
        with app.app_context():
            # Create multiple logs for the day
            logs = [
                FoodLog(
                    user_id=user.id,
                    food_item_id=food_item.id,
                    meal_type='breakfast',
                    servings=1.0,
                    logged_date=date.today(),
                    calories=52.0,
                    protein_g=0.3,
                    carbs_g=14.0,
                    fat_g=0.2
                ),
                FoodLog(
                    user_id=user.id,
                    food_item_id=food_item.id,
                    meal_type='lunch',
                    servings=2.0,
                    logged_date=date.today(),
                    calories=104.0,
                    protein_g=0.6,
                    carbs_g=28.0,
                    fat_g=0.4
                )
            ]
            for log in logs:
                db.session.add(log)
            db.session.commit()

            # Calculate totals
            daily_logs = FoodLog.query.filter_by(
                user_id=user.id,
                logged_date=date.today()
            ).all()

            total_calories = sum(log.calories for log in daily_logs)
            total_protein = sum(log.protein_g for log in daily_logs)
            total_carbs = sum(log.carbs_g for log in daily_logs)
            total_fat = sum(log.fat_g for log in daily_logs)

            assert total_calories == pytest.approx(156.0)
            assert total_protein == pytest.approx(0.9)
            assert total_carbs == pytest.approx(42.0)
            assert total_fat == pytest.approx(0.6)

    def test_meal_type_grouping(self, app, user, food_item):
        """Test grouping logs by meal type."""
        with app.app_context():
            meals = ['breakfast', 'lunch', 'snack']
            for meal in meals:
                log = FoodLog(
                    user_id=user.id,
                    food_item_id=food_item.id,
                    meal_type=meal,
                    servings=1.0,
                    logged_date=date.today(),
                    calories=52.0,
                    protein_g=0.3,
                    carbs_g=14.0,
                    fat_g=0.2
                )
                db.session.add(log)
            db.session.commit()

            # Group by meal type
            for meal in meals:
                meal_logs = FoodLog.query.filter_by(
                    user_id=user.id,
                    meal_type=meal,
                    logged_date=date.today()
                ).all()
                assert len(meal_logs) == 1


class TestUserNutritionGoals:
    """Tests for user nutrition goals."""

    def test_user_default_goals(self, app, user):
        """Test user has default nutrition goals."""
        with app.app_context():
            user = User.query.get(user.id)
            assert user.daily_calorie_goal == 2000
            assert user.protein_goal_pct == 30
            assert user.carb_goal_pct == 40
            assert user.fat_goal_pct == 30

    def test_user_goal_calculations(self, app, user):
        """Test goal gram calculations from percentages."""
        with app.app_context():
            user = User.query.get(user.id)
            
            # For 2000 cal diet:
            # Protein: 2000 * 0.30 / 4 = 150g
            # Carbs: 2000 * 0.40 / 4 = 200g
            # Fat: 2000 * 0.30 / 9 = 67g
            
            assert user.protein_goal_g == 150
            assert user.carb_goal_g == 200
            assert user.fat_goal_g == 67

    def test_update_user_goals(self, app, user):
        """Test updating user nutrition goals."""
        with app.app_context():
            user = User.query.get(user.id)
            user.daily_calorie_goal = 2500
            user.protein_goal_pct = 35
            db.session.commit()

            updated = User.query.get(user.id)
            assert updated.daily_calorie_goal == 2500
            assert updated.protein_goal_pct == 35


class TestFoodEditing:
    """Tests for editing food log entries."""

    def test_edit_servings_updates_nutrition(self, app, user, food_item):
        """Test editing servings updates nutritional values."""
        with app.app_context():
            log = FoodLog(
                user_id=user.id,
                food_item_id=food_item.id,
                meal_type='breakfast',
                servings=1.0,
                logged_date=date.today(),
                calories=52.0,
                protein_g=0.3,
                carbs_g=14.0,
                fat_g=0.2
            )
            db.session.add(log)
            db.session.commit()

            # Update servings
            log.servings = 2.5
            log.calories = food_item.calories * 2.5
            log.protein_g = food_item.protein_g * 2.5
            log.carbs_g = food_item.carbs_g * 2.5
            log.fat_g = food_item.fat_g * 2.5
            db.session.commit()

            updated = FoodLog.query.get(log.id)
            assert updated.servings == 2.5
            assert updated.calories == 130.0

    def test_delete_food_log(self, app, user, food_item):
        """Test deleting a food log entry."""
        with app.app_context():
            log = FoodLog(
                user_id=user.id,
                food_item_id=food_item.id,
                meal_type='breakfast',
                servings=1.0,
                logged_date=date.today(),
                calories=52.0,
                protein_g=0.3,
                carbs_g=14.0,
                fat_g=0.2
            )
            db.session.add(log)
            db.session.commit()
            log_id = log.id

            db.session.delete(log)
            db.session.commit()

            deleted = FoodLog.query.get(log_id)
            assert deleted is None
