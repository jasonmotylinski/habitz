from datetime import datetime
import secrets

from shared import db
from shared.user import User  # noqa: F401 – re-exported for sub-app imports

# Association table for meal favorites
meal_favorites = db.Table(
    'meal_favorites',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('meal_id', db.Integer, db.ForeignKey('meal.id'), primary_key=True)
)

class Household(db.Model):
    """Household for shared meal planning"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    members = db.relationship('User', backref='household', lazy='dynamic', foreign_keys='User.household_id')
    meal_plans = db.relationship('MealPlan', backref='household', lazy='dynamic', cascade='all, delete-orphan')
    shopping_lists = db.relationship('ShoppingList', backref='household', lazy='dynamic', cascade='all, delete-orphan')
    invites = db.relationship('HouseholdInvite', backref='household', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Household {self.name}>'

class HouseholdInvite(db.Model):
    """Secure invite tokens for household membership"""
    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey('household.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)  # URL-safe random token
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)  # 7 days from creation

    # One-time use tracking
    accepted = db.Column(db.Boolean, default=False)
    accepted_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    accepted_at = db.Column(db.DateTime)

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='invites_sent')
    acceptor = db.relationship('User', foreign_keys=[accepted_by])

    def is_valid(self):
        """Check if invite is still valid"""
        from datetime import datetime
        return not self.accepted and datetime.utcnow() < self.expires_at

    def __repr__(self):
        return f'<HouseholdInvite {self.token[:8]}... for {self.household.name}>'


class ApiKey(db.Model):
    """API key for external integrations"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    @staticmethod
    def generate_key():
        """Generate a new API key"""
        return secrets.token_urlsafe(48)

    def __repr__(self):
        return f'<ApiKey {self.name}>'

class Meal(db.Model):
    """Meal/Recipe model"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    image_filename = db.Column(db.String(255))
    ingredients = db.Column(db.Text)  # Comma-separated or JSON
    instructions = db.Column(db.Text)
    category = db.Column(db.String(50))  # Breakfast, Lunch, Dinner, Side, Dessert, etc.
    source_url = db.Column(db.String(512))  # URL where recipe was imported from
    source_name = db.Column(db.String(255))  # Domain name (e.g., "allrecipes.com")
    household_id = db.Column(db.Integer, db.ForeignKey('household.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Meal {self.name}>'

    def is_favorite_by(self, user):
        """Check if meal is favorited by user"""
        return user.favorites.filter(meal_favorites.c.meal_id == self.id).first() is not None

class MealPlan(db.Model):
    """Weekly meal plan (shared within household)"""
    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey('household.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    meal_type = db.Column(db.String(20), nullable=False)  # breakfast, lunch, dinner
    meal_id = db.Column(db.Integer, db.ForeignKey('meal.id'))
    custom_entry = db.Column(db.String(255))  # For "Leftovers", "Out to eat", etc.
    source_url = db.Column(db.String(512))  # Tracks URL for import
    import_status = db.Column(db.String(20), default='imported')  # imported, pending, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meal = db.relationship('Meal', backref='meal_plans')

    def __repr__(self):
        return f'<MealPlan {self.date} {self.meal_type}>'

class ShoppingList(db.Model):
    """Shopping list for a week (shared within household)"""
    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey('household.id'), nullable=False)
    store_name = db.Column(db.String(255), nullable=False)  # e.g., "Stop & Shop", "Costco"
    week_start_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = db.relationship('ShoppingListItem', backref='shopping_list', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ShoppingList {self.store_name} {self.week_start_date}>'

class ShoppingListItem(db.Model):
    """Item in a shopping list"""
    id = db.Column(db.Integer, primary_key=True)
    shopping_list_id = db.Column(db.Integer, db.ForeignKey('shopping_list.id'), nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.String(50))
    unit = db.Column(db.String(50))  # cups, tbsp, lbs, etc.
    meal_id = db.Column(db.Integer, db.ForeignKey('meal.id'))
    is_checked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meal = db.relationship('Meal', backref='shopping_items')

    def __repr__(self):
        return f'<ShoppingListItem {self.item_name}>'
