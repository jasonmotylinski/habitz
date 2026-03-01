"""Tests for meal planner API endpoints."""
import pytest
from datetime import datetime, date, timedelta
from meal_planner.models import Household, Meal, MealPlan, ShoppingList, ShoppingListItem, HouseholdInvite, ApiKey
from shared import db
from shared.user import User


@pytest.fixture
def household(app, user):
    """Create a test household."""
    with app.app_context():
        hh = Household(
            name='Test Household',
            created_by=user.id
        )
        db.session.add(hh)
        db.session.commit()
        return hh


@pytest.fixture
def meal(app, household, user):
    """Create a test meal."""
    with app.app_context():
        meal = Meal(
            name='Spaghetti',
            description='Classic pasta dish',
            ingredients='Pasta, tomato sauce, garlic, olive oil',
            instructions='Boil pasta, make sauce, combine',
            category='Dinner',
            household_id=household.id,
            created_by=user.id
        )
        db.session.add(meal)
        db.session.commit()
        return meal


class TestHouseholdManagement:
    """Tests for household creation and management."""

    def test_create_household(self, app, user):
        """Test creating a household."""
        with app.app_context():
            hh = Household(
                name='Family',
                created_by=user.id
            )
            db.session.add(hh)
            db.session.commit()

            assert hh.id is not None
            assert hh.name == 'Family'
            assert hh.created_by == user.id

    def test_household_has_creator(self, app, household, user):
        """Test household creator relationship."""
        with app.app_context():
            hh = Household.query.get(household.id)
            creator = User.query.get(hh.created_by)
            assert creator.email == user.email

    def test_multiple_households(self, app, user):
        """Test user can have multiple households."""
        with app.app_context():
            hh1 = Household(name='Home', created_by=user.id)
            hh2 = Household(name='Work', created_by=user.id)
            db.session.add_all([hh1, hh2])
            db.session.commit()

            households = Household.query.filter_by(created_by=user.id).all()
            assert len(households) == 2


class TestMealCreation:
    """Tests for meal/recipe creation."""

    def test_create_meal(self, app, household, user):
        """Test creating a meal."""
        with app.app_context():
            meal = Meal(
                name='Tacos',
                description='Mexican street tacos',
                ingredients='Tortillas, beef, lettuce, cheese',
                category='Lunch',
                household_id=household.id,
                created_by=user.id
            )
            db.session.add(meal)
            db.session.commit()

            assert meal.id is not None
            assert meal.name == 'Tacos'

    def test_meal_with_instructions(self, meal):
        """Test meal with detailed instructions."""
        assert meal.instructions == 'Boil pasta, make sauce, combine'
        assert meal.category == 'Dinner'

    def test_meal_with_source_url(self, app, household, user):
        """Test importing meal from source URL."""
        with app.app_context():
            meal = Meal(
                name='Cookie Recipe',
                source_url='https://example.com/recipe',
                source_name='example.com',
                household_id=household.id,
                created_by=user.id
            )
            db.session.add(meal)
            db.session.commit()

            assert meal.source_url == 'https://example.com/recipe'
            assert meal.source_name == 'example.com'

    def test_household_meals_query(self, app, household, user, meal):
        """Test querying meals by household."""
        with app.app_context():
            # Create another meal
            meal2 = Meal(
                name='Pizza',
                household_id=household.id,
                created_by=user.id
            )
            db.session.add(meal2)
            db.session.commit()

            meals = Meal.query.filter_by(household_id=household.id).all()
            assert len(meals) == 2


class TestMealFavorites:
    """Tests for marking meals as favorites."""

    def test_favorite_meal(self, app, user, meal):
        """Test favoriting a meal."""
        with app.app_context():
            user = User.query.get(user.id)
            meal = Meal.query.get(meal.id)
            
            user.favorites.append(meal)
            db.session.commit()

            assert meal in user.favorites

    def test_unfavorite_meal(self, app, user, meal):
        """Test removing meal from favorites."""
        with app.app_context():
            user = User.query.get(user.id)
            meal = Meal.query.get(meal.id)
            
            user.favorites.append(meal)
            db.session.commit()
            
            user.favorites.remove(meal)
            db.session.commit()

            assert meal not in user.favorites

    def test_is_favorite_by_user(self, app, user, meal):
        """Test checking if meal is favorited by user."""
        with app.app_context():
            user = User.query.get(user.id)
            meal = Meal.query.get(meal.id)
            
            assert not meal.is_favorite_by(user)
            
            user.favorites.append(meal)
            db.session.commit()
            
            assert meal.is_favorite_by(user)


class TestMealPlanning:
    """Tests for meal planning functionality."""

    def test_create_meal_plan_entry(self, app, household, meal):
        """Test creating a meal plan entry."""
        with app.app_context():
            plan = MealPlan(
                household_id=household.id,
                date=date.today(),
                meal_type='dinner',
                meal_id=meal.id
            )
            db.session.add(plan)
            db.session.commit()

            assert plan.id is not None
            assert plan.meal_id == meal.id

    def test_custom_meal_plan_entry(self, app, household):
        """Test creating custom meal plan entry."""
        with app.app_context():
            plan = MealPlan(
                household_id=household.id,
                date=date.today(),
                meal_type='lunch',
                custom_entry='Leftovers'
            )
            db.session.add(plan)
            db.session.commit()

            assert plan.custom_entry == 'Leftovers'
            assert plan.meal_id is None

    def test_get_household_meal_plan_for_week(self, app, household, meal):
        """Test querying meal plan for a week."""
        with app.app_context():
            # Create meal plans for a week
            today = date.today()
            for i in range(7):
                plan = MealPlan(
                    household_id=household.id,
                    date=today + timedelta(days=i),
                    meal_type='dinner',
                    meal_id=meal.id
                )
                db.session.add(plan)
            db.session.commit()

            week_plans = MealPlan.query.filter(
                MealPlan.household_id == household.id,
                MealPlan.date >= today,
                MealPlan.date < today + timedelta(days=7)
            ).all()

            assert len(week_plans) == 7

    def test_meal_type_filtering(self, app, household, meal):
        """Test filtering meal plans by meal type."""
        with app.app_context():
            plan1 = MealPlan(household_id=household.id, date=date.today(), meal_type='breakfast', meal_id=meal.id)
            plan2 = MealPlan(household_id=household.id, date=date.today(), meal_type='lunch', meal_id=meal.id)
            plan3 = MealPlan(household_id=household.id, date=date.today(), meal_type='dinner', meal_id=meal.id)
            
            db.session.add_all([plan1, plan2, plan3])
            db.session.commit()

            dinners = MealPlan.query.filter_by(
                household_id=household.id,
                meal_type='dinner'
            ).all()

            assert len(dinners) == 1
            assert dinners[0].meal_type == 'dinner'


class TestShoppingList:
    """Tests for shopping list functionality."""

    def test_create_shopping_list(self, app, household):
        """Test creating a shopping list."""
        with app.app_context():
            shopping = ShoppingList(
                household_id=household.id,
                store_name='Whole Foods',
                week_start_date=date.today()
            )
            db.session.add(shopping)
            db.session.commit()

            assert shopping.id is not None
            assert shopping.store_name == 'Whole Foods'

    def test_add_item_to_shopping_list(self, app, household):
        """Test adding items to shopping list."""
        with app.app_context():
            shopping = ShoppingList(
                household_id=household.id,
                store_name='Target',
                week_start_date=date.today()
            )
            db.session.add(shopping)
            db.session.commit()

            item = ShoppingListItem(
                shopping_list_id=shopping.id,
                item_name='Milk',
                quantity='2',
                unit='gallons'
            )
            db.session.add(item)
            db.session.commit()

            assert item.id is not None
            assert shopping.items.count() == 1

    def test_check_off_shopping_item(self, app, household):
        """Test marking shopping item as purchased."""
        with app.app_context():
            shopping = ShoppingList(
                household_id=household.id,
                store_name='Kroger',
                week_start_date=date.today()
            )
            db.session.add(shopping)
            db.session.flush()

            item = ShoppingListItem(
                shopping_list_id=shopping.id,
                item_name='Eggs',
                is_checked=False
            )
            db.session.add(item)
            db.session.commit()

            # Check it off
            item.is_checked = True
            db.session.commit()

            assert item.is_checked is True

    def test_shopping_list_items_from_meal(self, app, household, meal):
        """Test adding shopping list items from a meal."""
        with app.app_context():
            shopping = ShoppingList(
                household_id=household.id,
                store_name='Whole Foods',
                week_start_date=date.today()
            )
            db.session.add(shopping)
            db.session.commit()

            item = ShoppingListItem(
                shopping_list_id=shopping.id,
                item_name='Pasta',
                meal_id=meal.id
            )
            db.session.add(item)
            db.session.commit()

            assert item.meal_id == meal.id


class TestHouseholdInvites:
    """Tests for household invite system."""

    def test_create_invite(self, app, household, user):
        """Test creating a household invite."""
        with app.app_context():
            expires = datetime.utcnow() + timedelta(days=7)
            invite = HouseholdInvite(
                household_id=household.id,
                created_by=user.id,
                expires_at=expires
            )
            invite.token = ApiKey.generate_key()
            db.session.add(invite)
            db.session.commit()

            assert invite.id is not None
            assert invite.token is not None

    def test_invite_validity_check(self, app, household, user):
        """Test checking if invite is valid."""
        with app.app_context():
            # Valid invite
            expires_valid = datetime.utcnow() + timedelta(days=7)
            valid_invite = HouseholdInvite(
                household_id=household.id,
                created_by=user.id,
                expires_at=expires_valid,
                accepted=False
            )
            valid_invite.token = ApiKey.generate_key()
            db.session.add(valid_invite)
            db.session.commit()

            assert valid_invite.is_valid() is True

    def test_expired_invite(self, app, household, user):
        """Test expired invite is not valid."""
        with app.app_context():
            expires_past = datetime.utcnow() - timedelta(days=1)
            expired = HouseholdInvite(
                household_id=household.id,
                created_by=user.id,
                expires_at=expires_past,
                accepted=False
            )
            expired.token = ApiKey.generate_key()
            db.session.add(expired)
            db.session.commit()

            assert expired.is_valid() is False

    def test_accept_invite(self, app, household, user):
        """Test accepting a household invite."""
        with app.app_context():
            user2_id = 999  # Simulated other user
            expires = datetime.utcnow() + timedelta(days=7)
            invite = HouseholdInvite(
                household_id=household.id,
                created_by=user.id,
                expires_at=expires,
                accepted=False
            )
            invite.token = ApiKey.generate_key()
            db.session.add(invite)
            db.session.commit()

            # Accept invite
            invite.accepted = True
            invite.accepted_by = user2_id
            invite.accepted_at = datetime.utcnow()
            db.session.commit()

            assert invite.accepted is True


class TestApiKeys:
    """Tests for API key management."""

    def test_generate_api_key(self, app, user):
        """Test generating an API key."""
        with app.app_context():
            key = ApiKey.generate_key()
            assert isinstance(key, str)
            assert len(key) > 20

    def test_create_api_key(self, app, user):
        """Test creating an API key for user."""
        with app.app_context():
            api_key = ApiKey(
                user_id=user.id,
                name='Mobile App',
                key=ApiKey.generate_key()
            )
            db.session.add(api_key)
            db.session.commit()

            assert api_key.id is not None
            assert api_key.is_active is True

    def test_deactivate_api_key(self, app, user):
        """Test deactivating an API key."""
        with app.app_context():
            api_key = ApiKey(
                user_id=user.id,
                key=ApiKey.generate_key()
            )
            db.session.add(api_key)
            db.session.commit()

            api_key.is_active = False
            db.session.commit()

            assert api_key.is_active is False
