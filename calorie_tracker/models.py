from datetime import date, datetime

from shared import db
from shared.user import User  # noqa: F401 – re-exported for sub-app imports


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
