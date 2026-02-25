from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    default_fast_hours = db.Column(db.Integer, default=16)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    fasts = db.relationship('Fast', backref='user', lazy='dynamic',
                            cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'default_fast_hours': self.default_fast_hours,
        }


class Fast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    target_hours = db.Column(db.Integer, nullable=False, default=16)
    ended_at = db.Column(db.DateTime, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_active(self):
        return self.ended_at is None

    @property
    def duration_seconds(self):
        end = self.ended_at or datetime.utcnow()
        return (end - self.started_at).total_seconds()

    @property
    def target_seconds(self):
        return self.target_hours * 3600

    @property
    def progress_pct(self):
        if self.target_seconds == 0:
            return 100.0
        return min(100.0, (self.duration_seconds / self.target_seconds) * 100)

    def to_dict(self):
        result = {
            'id': self.id,
            'started_at': self.started_at.isoformat() + 'Z',
            'target_hours': self.target_hours,
            'target_seconds': self.target_seconds,
            'duration_seconds': self.duration_seconds,
            'progress_pct': round(self.progress_pct, 1),
            'completed': self.completed,
            'note': self.note,
        }
        if self.is_active:
            remaining = max(0, self.target_seconds - self.duration_seconds)
            result['remaining_seconds'] = remaining
        else:
            result['ended_at'] = self.ended_at.isoformat() + 'Z'
        return result
