from datetime import datetime, timezone

from .. import db


class WorkoutLog(db.Model):
    __tablename__ = "workout_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=True)
    workout_id = db.Column(db.Integer, db.ForeignKey("workouts.id"), nullable=True)
    custom_name = db.Column(db.String(200), nullable=True)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    body_weight = db.Column(db.Float, nullable=True)

    workout = db.relationship("Workout")
    sets = db.relationship(
        "SetLog",
        backref="workout_log",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="SetLog.id",
    )

    def to_dict(self, include_sets=False):
        data = {
            "id": self.id,
            "program_id": self.program_id,
            "workout_id": self.workout_id,
            "workout_name": self.custom_name if self.workout_id is None else self.workout.name,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "notes": self.notes,
            "body_weight": self.body_weight,
        }
        if include_sets:
            data["sets"] = [s.to_dict() for s in self.sets.order_by(SetLog.exercise_id, SetLog.set_number)]
        return data


class SetLog(db.Model):
    __tablename__ = "set_logs"

    id = db.Column(db.Integer, primary_key=True)
    workout_log_id = db.Column(db.Integer, db.ForeignKey("workout_logs.id"), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False)
    set_number = db.Column(db.Integer, nullable=False)
    planned_reps = db.Column(db.Integer, nullable=True)
    actual_reps = db.Column(db.Integer, nullable=True)
    weight = db.Column(db.Float, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    completed = db.Column(db.Boolean, default=False)

    exercise = db.relationship("Exercise")

    def to_dict(self):
        return {
            "id": self.id,
            "exercise_id": self.exercise_id,
            "exercise_name": self.exercise.name,
            "exercise_type": self.exercise.type,
            "set_number": self.set_number,
            "planned_reps": self.planned_reps,
            "actual_reps": self.actual_reps,
            "weight": self.weight,
            "duration_minutes": self.duration_minutes,
            "completed": self.completed,
        }
