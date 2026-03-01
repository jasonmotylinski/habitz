from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from . import db


class User(UserMixin, db.Model):
    """Unified user model shared across all Habitz sub-apps."""
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True)  # nullable – workout tracker doesn't use it
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # meal_planner: household membership
    household_id = db.Column(db.Integer, db.ForeignKey('household.id'), nullable=True)

    # calorie_tracker: daily nutrition goals
    daily_calorie_goal = db.Column(db.Integer, default=2000)
    protein_goal_pct = db.Column(db.Integer, default=30)
    carb_goal_pct = db.Column(db.Integer, default=40)
    fat_goal_pct = db.Column(db.Integer, default=30)

    # fasting_tracker: default fast duration
    default_fast_hours = db.Column(db.Integer, default=16)

    # user timezone (IANA timezone name)
    timezone = db.Column(db.String(50), default='America/New_York')

    # workout_tracker relationships (string refs resolved lazily at mapper config time)
    programs = db.relationship("Program", backref="user", lazy="dynamic")
    workouts = db.relationship("Workout", backref="user", lazy="dynamic")
    exercises = db.relationship("Exercise", backref="user", lazy="dynamic")
    workout_logs = db.relationship("WorkoutLog", backref="user", lazy="dynamic")

    # calorie_tracker relationships
    food_logs = db.relationship(
        'FoodLog', backref='user', lazy='dynamic', cascade='all, delete-orphan'
    )

    # fasting_tracker relationships
    fasts = db.relationship(
        'Fast', backref='user', lazy='dynamic', cascade='all, delete-orphan'
    )

    # meal_planner relationships
    meals = db.relationship(
        'Meal', backref='creator', lazy='dynamic', foreign_keys='Meal.created_by'
    )
    favorites = db.relationship(
        'Meal', secondary='meal_favorites', lazy='dynamic',
        backref=db.backref('favorited_by', lazy='dynamic'),
    )
    api_keys = db.relationship('ApiKey', backref='user')

    # --- auth ---

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # Legacy bcrypt hashes (workout_tracker used Flask-Bcrypt before consolidation).
        # Verify with bcrypt, then silently re-hash to werkzeug format and commit so
        # the upgrade is permanent and bcrypt is no longer needed after first login.
        if self.password_hash and self.password_hash.startswith(('$2b$', '$2a$')):
            import bcrypt as _bcrypt
            ok = _bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
            if ok:
                self.set_password(password)
                from . import db
                db.session.commit()
            return ok
        return check_password_hash(self.password_hash, password)

    # --- calorie_tracker computed properties ---

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
            'created_at': self.created_at.isoformat(),
            'daily_calorie_goal': self.daily_calorie_goal,
            'protein_goal_pct': self.protein_goal_pct,
            'carb_goal_pct': self.carb_goal_pct,
            'fat_goal_pct': self.fat_goal_pct,
            'protein_goal_g': self.protein_goal_g,
            'carb_goal_g': self.carb_goal_g,
            'fat_goal_g': self.fat_goal_g,
            'default_fast_hours': self.default_fast_hours,
        }
