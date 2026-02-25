from .. import db


class Workout(db.Model):
    __tablename__ = "workouts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)

    workout_exercises = db.relationship(
        "WorkoutExercise",
        backref="workout",
        lazy="dynamic",
        order_by="WorkoutExercise.position",
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_exercises=False):
        data = {
            "id": self.id,
            "name": self.name,
        }
        if include_exercises:
            data["exercises"] = [
                we.to_dict()
                for we in self.workout_exercises.order_by(WorkoutExercise.position)
            ]
        return data


class WorkoutExercise(db.Model):
    __tablename__ = "workout_exercises"

    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey("workouts.id"), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    default_sets = db.Column(db.Integer, default=5)
    default_reps = db.Column(db.Integer, default=5)
    default_weight = db.Column(db.Float, nullable=True)
    default_duration_minutes = db.Column(db.Integer, nullable=True)
    unit = db.Column(db.String(20), default="reps")

    exercise = db.relationship("Exercise")

    def to_dict(self):
        return {
            "id": self.id,
            "exercise_id": self.exercise_id,
            "exercise_name": self.exercise.name,
            "exercise_type": self.exercise.type,
            "position": self.position,
            "default_sets": self.default_sets,
            "default_reps": self.default_reps,
            "default_weight": self.default_weight,
            "default_duration_minutes": self.default_duration_minutes,
            "unit": self.unit,
        }
