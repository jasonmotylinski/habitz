from datetime import datetime, timezone

from flask_login import UserMixin

from .. import db, bcrypt, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    programs = db.relationship("Program", backref="user", lazy="dynamic")
    workouts = db.relationship("Workout", backref="user", lazy="dynamic")
    exercises = db.relationship("Exercise", backref="user", lazy="dynamic")
    workout_logs = db.relationship("WorkoutLog", backref="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
        }


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
