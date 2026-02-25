from datetime import date, datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    daily_calorie_goal = db.Column(db.Integer, default=2000)
    protein_goal_pct = db.Column(db.Integer, default=30)
    carb_goal_pct = db.Column(db.Integer, default=40)
    fat_goal_pct = db.Column(db.Integer, default=30)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    food_logs = db.relationship('FoodLog', backref='user', lazy='dynamic',
                                cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def protein_goal_g(self):
        return round((self.daily_calorie_goal * self.protein_goal_pct / 100) / 4)

    @property
    def carb_goal_g(self):
        return round((self.daily_calorie_goal * self.carb_goal_pct / 100) / 4)

    @property
    def fat_goal_g(self):
        return round((self.daily_calorie_goal * self.fat_goal_pct / 100) / 9)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'daily_calorie_goal': self.daily_calorie_goal,
            'protein_goal_pct': self.protein_goal_pct,
            'carb_goal_pct': self.carb_goal_pct,
            'fat_goal_pct': self.fat_goal_pct,
            'protein_goal_g': self.protein_goal_g,
            'carb_goal_g': self.carb_goal_g,
            'fat_goal_g': self.fat_goal_g,
        }


class FoodItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(200))
    source = db.Column(db.String(20), nullable=False)  # 'usda', 'openfoodfacts', 'custom'
    source_id = db.Column(db.String(100))
    calories = db.Column(db.Float, nullable=False)
    protein_g = db.Column(db.Float, default=0)
    carbs_g = db.Column(db.Float, default=0)
    fat_g = db.Column(db.Float, default=0)
    fiber_g = db.Column(db.Float)
    serving_size = db.Column(db.String(100))
    serving_weight_g = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    logs = db.relationship('FoodLog', backref='food_item', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'source': self.source,
            'source_id': self.source_id,
            'calories': self.calories,
            'protein_g': self.protein_g,
            'carbs_g': self.carbs_g,
            'fat_g': self.fat_g,
            'fiber_g': self.fiber_g,
            'serving_size': self.serving_size,
            'serving_weight_g': self.serving_weight_g,
        }


class UsdaFood(db.Model):
    """OpenNutrition food database. All nutrient values are per 100g."""
    food_id = db.Column(db.String(30), primary_key=True)
    name = db.Column(db.String(300), nullable=False, index=True)
    food_type = db.Column(db.String(20))          # everyday, grocery, restaurant, prepared
    alternate_names = db.Column(db.Text)           # space-joined aliases for search
    barcode = db.Column(db.String(20), index=True) # EAN-13 for future barcode scanning
    calories = db.Column(db.Float, default=0)
    protein_g = db.Column(db.Float, default=0)
    carbs_g = db.Column(db.Float, default=0)
    fat_g = db.Column(db.Float, default=0)
    fiber_g = db.Column(db.Float)
    serving_description = db.Column(db.String(100))
    serving_weight_g = db.Column(db.Float)

    def to_search_result(self):
        """Return a dict shaped like the API search result."""
        serving_g = self.serving_weight_g or 100
        scale = serving_g / 100
        return {
            'name': self.name,
            'brand': None,
            'source': 'opennutrition',
            'source_id': self.food_id,
            'calories': round((self.calories or 0) * scale, 1),
            'protein_g': round((self.protein_g or 0) * scale, 1),
            'carbs_g': round((self.carbs_g or 0) * scale, 1),
            'fat_g': round((self.fat_g or 0) * scale, 1),
            'fiber_g': round((self.fiber_g or 0) * scale, 1) if self.fiber_g else None,
            'serving_size': self.serving_description or '100g',
            'serving_weight_g': serving_g,
        }


class FoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    food_item_id = db.Column(db.Integer, db.ForeignKey('food_item.id'), nullable=False)
    meal_type = db.Column(db.String(20), nullable=False)  # breakfast, lunch, dinner, snack
    servings = db.Column(db.Float, default=1.0)
    logged_date = db.Column(db.Date, nullable=False, default=date.today)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)
    calories = db.Column(db.Float, nullable=False)
    protein_g = db.Column(db.Float, default=0)
    carbs_g = db.Column(db.Float, default=0)
    fat_g = db.Column(db.Float, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'food_item': self.food_item.to_dict() if self.food_item else None,
            'meal_type': self.meal_type,
            'servings': self.servings,
            'logged_date': self.logged_date.isoformat(),
            'calories': self.calories,
            'protein_g': self.protein_g,
            'carbs_g': self.carbs_g,
            'fat_g': self.fat_g,
        }
