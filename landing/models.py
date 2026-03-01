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


class DailyNote(db.Model):
    """Daily note for a specific date"""
    __tablename__ = 'daily_note'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date       = db.Column(db.Date, nullable=False)
    content    = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'date'),)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class DailyMood(db.Model):
    """Daily mood tracking for a specific date"""
    __tablename__ = 'daily_mood'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date       = db.Column(db.Date, nullable=False)
    mood       = db.Column(db.Integer, nullable=False)  # 1-5 scale: 1=terrible, 5=excellent
    emoji      = db.Column(db.String(10), nullable=True)  # Optional emoji (😢😕😐😊😄)
    notes      = db.Column(db.Text, nullable=True)  # Optional notes about mood
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'date'),)

    MOOD_EMOJIS = {
        1: '😢',
        2: '😕',
        3: '😐',
        4: '😊',
        5: '😄',
    }

    @staticmethod
    def get_emoji_for_mood(mood):
        """Get emoji for a mood score (1-5)"""
        return DailyMood.MOOD_EMOJIS.get(mood, '😐')

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'mood': self.mood,
            'emoji': self.emoji or self.get_emoji_for_mood(self.mood),
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
