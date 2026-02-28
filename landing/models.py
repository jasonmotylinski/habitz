from datetime import datetime

from shared import db


class Habit(db.Model):
    __tablename__ = 'habit'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name        = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), default='')
    habit_type  = db.Column(db.String(20), nullable=False, default='manual')
    # 'manual' | 'workout' | 'calories' | 'fasting' | 'meals'
    icon        = db.Column(db.String(10), default='✓')
    color       = db.Column(db.String(7), default='#4A90E2')
    sort_order  = db.Column(db.Integer, default=0)
    active      = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    logs = db.relationship('HabitLog', backref='habit', lazy='dynamic',
                           cascade='all, delete-orphan')


class HabitLog(db.Model):
    __tablename__ = 'habit_log'

    id             = db.Column(db.Integer, primary_key=True)
    habit_id       = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    completed_date = db.Column(db.Date, nullable=False)
    completed_at   = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('habit_id', 'completed_date'),)
