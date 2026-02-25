from datetime import datetime, timezone

from .. import db


class Program(db.Model):
    __tablename__ = "programs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    workout_order = db.relationship(
        "ProgramWorkoutOrder",
        backref="program",
        lazy="dynamic",
        order_by="ProgramWorkoutOrder.position",
        cascade="all, delete-orphan",
    )
    logs = db.relationship("WorkoutLog", backref="program", lazy="dynamic")

    def to_dict(self, include_workouts=False):
        data = {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
        }
        if include_workouts:
            data["workouts"] = [
                {
                    "id": pw.workout.id,
                    "name": pw.workout.name,
                    "position": pw.position,
                    "exercises": [
                        we.exercise.name
                        for we in pw.workout.workout_exercises.order_by(
                            WorkoutExerciseProxy.position
                        )
                    ],
                }
                for pw in self.workout_order.order_by(ProgramWorkoutOrder.position)
            ]
        return data


class ProgramWorkoutOrder(db.Model):
    __tablename__ = "program_workout_order"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=False)
    workout_id = db.Column(db.Integer, db.ForeignKey("workouts.id"), nullable=False)
    position = db.Column(db.Integer, nullable=False)

    workout = db.relationship("Workout")


# Avoid circular import — we just need the class for ordering
from .workout import WorkoutExercise as WorkoutExerciseProxy  # noqa: E402
