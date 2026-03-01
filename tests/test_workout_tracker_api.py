"""Tests for workout tracker API endpoints."""
import pytest
from datetime import datetime, timezone
from workout_tracker.models.program import Program, ProgramWorkoutOrder
from workout_tracker.models.workout import Workout, WorkoutExercise
from workout_tracker.models.exercise import Exercise
from workout_tracker.models.log import WorkoutLog, SetLog
from shared import db
from shared.user import User


@pytest.fixture
def exercise(app, user):
    """Create a test exercise."""
    with app.app_context():
        ex = Exercise(
            user_id=user.id,
            name='Bench Press',
            type='strength',
            unit='reps'
        )
        db.session.add(ex)
        db.session.commit()
        return ex


@pytest.fixture
def workout(app, user, exercise):
    """Create a test workout with exercises."""
    with app.app_context():
        wo = Workout(
            user_id=user.id,
            name='Chest Day'
        )
        db.session.add(wo)
        db.session.flush()

        we = WorkoutExercise(
            workout_id=wo.id,
            exercise_id=exercise.id,
            position=0,
            default_sets=4,
            default_reps=8,
            default_weight=225.0
        )
        db.session.add(we)
        db.session.commit()
        return wo


@pytest.fixture
def program(app, user, workout):
    """Create a test program."""
    with app.app_context():
        prog = Program(
            user_id=user.id,
            name='Push/Pull/Legs'
        )
        db.session.add(prog)
        db.session.flush()

        pwo = ProgramWorkoutOrder(
            program_id=prog.id,
            workout_id=workout.id,
            position=0
        )
        db.session.add(pwo)
        db.session.commit()
        return prog


class TestExerciseManagement:
    """Tests for exercise creation and management."""

    def test_create_strength_exercise(self, app, user):
        """Test creating a strength exercise."""
        with app.app_context():
            ex = Exercise(
                user_id=user.id,
                name='Squat',
                type='strength',
                unit='reps'
            )
            db.session.add(ex)
            db.session.commit()

            assert ex.id is not None
            assert ex.type == 'strength'

    def test_create_cardio_exercise(self, app, user):
        """Test creating a cardio exercise."""
        with app.app_context():
            ex = Exercise(
                user_id=user.id,
                name='Running',
                type='cardio',
                unit='mins'
            )
            db.session.add(ex)
            db.session.commit()

            assert ex.type == 'cardio'
            assert ex.unit == 'mins'

    def test_exercise_to_dict(self, exercise):
        """Test exercise serialization."""
        data = exercise.to_dict()

        assert data['name'] == 'Bench Press'
        assert data['type'] == 'strength'
        assert data['unit'] == 'reps'

    def test_user_exercises_query(self, app, user):
        """Test querying exercises by user."""
        with app.app_context():
            ex1 = Exercise(user_id=user.id, name='Squat', type='strength')
            ex2 = Exercise(user_id=user.id, name='Deadlift', type='strength')
            db.session.add_all([ex1, ex2])
            db.session.commit()

            exercises = Exercise.query.filter_by(user_id=user.id).all()
            assert len(exercises) == 2


class TestWorkoutCreation:
    """Tests for workout creation."""

    def test_create_workout(self, app, user):
        """Test creating a workout."""
        with app.app_context():
            wo = Workout(
                user_id=user.id,
                name='Upper Body'
            )
            db.session.add(wo)
            db.session.commit()

            assert wo.id is not None
            assert wo.name == 'Upper Body'

    def test_add_exercise_to_workout(self, app, user, exercise, workout):
        """Test adding exercise to workout."""
        with app.app_context():
            ex = exercise
            wo = workout

            we = WorkoutExercise.query.filter_by(
                workout_id=wo.id,
                exercise_id=ex.id
            ).first()

            assert we is not None
            assert we.default_sets == 4
            assert we.default_reps == 8

    def test_workout_exercise_to_dict(self, workout):
        """Test workout exercise serialization."""
        with app.app_context():
            we = workout.workout_exercises.first()
            data = we.to_dict()

            assert data['exercise_name'] == 'Bench Press'
            assert data['default_sets'] == 4
            assert data['default_weight'] == 225.0

    def test_workout_to_dict_with_exercises(self, workout):
        """Test workout serialization with exercises."""
        with app.app_context():
            wo = workout
            data = wo.to_dict(include_exercises=True)

            assert data['name'] == 'Chest Day'
            assert 'exercises' in data
            assert len(data['exercises']) == 1

    def test_multiple_exercises_in_workout(self, app, user, exercise):
        """Test workout with multiple exercises."""
        with app.app_context():
            wo = Workout(user_id=user.id, name='Full Body')
            db.session.add(wo)
            db.session.flush()

            ex1 = exercise
            ex2 = Exercise(user_id=user.id, name='Squat', type='strength')
            db.session.add(ex2)
            db.session.flush()

            we1 = WorkoutExercise(workout_id=wo.id, exercise_id=ex1.id, position=0)
            we2 = WorkoutExercise(workout_id=wo.id, exercise_id=ex2.id, position=1)
            db.session.add_all([we1, we2])
            db.session.commit()

            exercises = wo.workout_exercises.all()
            assert len(exercises) == 2


class TestProgramManagement:
    """Tests for program management."""

    def test_create_program(self, app, user):
        """Test creating a program."""
        with app.app_context():
            prog = Program(
                user_id=user.id,
                name='5x5'
            )
            db.session.add(prog)
            db.session.commit()

            assert prog.id is not None
            assert prog.name == '5x5'

    def test_add_workouts_to_program(self, app, user):
        """Test adding workouts to a program."""
        with app.app_context():
            prog = Program(user_id=user.id, name='PPL')
            db.session.add(prog)
            db.session.flush()

            wo1 = Workout(user_id=user.id, name='Push')
            wo2 = Workout(user_id=user.id, name='Pull')
            db.session.add_all([wo1, wo2])
            db.session.flush()

            pwo1 = ProgramWorkoutOrder(program_id=prog.id, workout_id=wo1.id, position=0)
            pwo2 = ProgramWorkoutOrder(program_id=prog.id, workout_id=wo2.id, position=1)
            db.session.add_all([pwo1, pwo2])
            db.session.commit()

            workouts = prog.workout_order.all()
            assert len(workouts) == 2

    def test_program_to_dict_with_workouts(self, program):
        """Test program serialization with workouts."""
        with app.app_context():
            prog = program
            data = prog.to_dict(include_workouts=True)

            assert data['name'] == 'Push/Pull/Legs'
            assert 'workouts' in data

    def test_program_workout_order(self, app, user):
        """Test workout order in program."""
        with app.app_context():
            prog = Program(user_id=user.id, name='ABC')
            db.session.add(prog)
            db.session.flush()

            workouts = []
            for i, name in enumerate(['A', 'B', 'C']):
                wo = Workout(user_id=user.id, name=f'Workout {name}')
                db.session.add(wo)
                db.session.flush()
                pwo = ProgramWorkoutOrder(program_id=prog.id, workout_id=wo.id, position=i)
                db.session.add(pwo)
                workouts.append(wo)
            
            db.session.commit()

            ordered = prog.workout_order.all()
            assert ordered[0].position == 0
            assert ordered[1].position == 1
            assert ordered[2].position == 2


class TestWorkoutLogging:
    """Tests for logging workouts."""

    def test_create_workout_log(self, app, user, workout):
        """Test logging a workout."""
        with app.app_context():
            log = WorkoutLog(
                user_id=user.id,
                workout_id=workout.id,
                body_weight=185.0
            )
            db.session.add(log)
            db.session.commit()

            assert log.id is not None
            assert log.completed_at is None

    def test_custom_workout_log(self, app, user):
        """Test logging a custom workout."""
        with app.app_context():
            log = WorkoutLog(
                user_id=user.id,
                custom_name='Cardio Session',
                notes='30 min treadmill'
            )
            db.session.add(log)
            db.session.commit()

            assert log.custom_name == 'Cardio Session'
            assert log.workout_id is None

    def test_workout_log_with_program(self, app, user, program):
        """Test logging a workout with program reference."""
        with app.app_context():
            log = WorkoutLog(
                user_id=user.id,
                program_id=program.id
            )
            db.session.add(log)
            db.session.commit()

            assert log.program_id == program.id

    def test_complete_workout(self, app, user, workout):
        """Test completing a workout."""
        with app.app_context():
            log = WorkoutLog(
                user_id=user.id,
                workout_id=workout.id
            )
            db.session.add(log)
            db.session.commit()

            log.completed_at = datetime.now(timezone.utc)
            db.session.commit()

            updated = WorkoutLog.query.get(log.id)
            assert updated.completed_at is not None


class TestSetLogging:
    """Tests for logging individual sets."""

    def test_log_set(self, app, user, workout, exercise):
        """Test logging a single set."""
        with app.app_context():
            log = WorkoutLog(user_id=user.id, workout_id=workout.id)
            db.session.add(log)
            db.session.flush()

            set_log = SetLog(
                workout_log_id=log.id,
                exercise_id=exercise.id,
                set_number=1,
                planned_reps=8,
                actual_reps=8,
                weight=225.0,
                completed=True
            )
            db.session.add(set_log)
            db.session.commit()

            assert set_log.actual_reps == 8
            assert set_log.completed is True

    def test_log_multiple_sets(self, app, user, workout, exercise):
        """Test logging multiple sets."""
        with app.app_context():
            log = WorkoutLog(user_id=user.id, workout_id=workout.id)
            db.session.add(log)
            db.session.flush()

            for i in range(4):
                set_log = SetLog(
                    workout_log_id=log.id,
                    exercise_id=exercise.id,
                    set_number=i + 1,
                    planned_reps=8,
                    actual_reps=8 - i,  # Progressive fatigue
                    weight=225.0,
                    completed=True
                )
                db.session.add(set_log)
            
            db.session.commit()

            sets = log.sets.all()
            assert len(sets) == 4
            assert sets[0].actual_reps == 8
            assert sets[3].actual_reps == 5

    def test_cardio_set_logging(self, app, user):
        """Test logging cardio exercise."""
        with app.app_context():
            ex = Exercise(user_id=user.id, name='Treadmill', type='cardio', unit='mins')
            db.session.add(ex)
            db.session.flush()

            log = WorkoutLog(user_id=user.id, custom_name='Cardio')
            db.session.add(log)
            db.session.flush()

            set_log = SetLog(
                workout_log_id=log.id,
                exercise_id=ex.id,
                set_number=1,
                duration_minutes=30,
                completed=True
            )
            db.session.add(set_log)
            db.session.commit()

            assert set_log.duration_minutes == 30

    def test_set_log_to_dict(self, app, user, workout, exercise):
        """Test set log serialization."""
        with app.app_context():
            log = WorkoutLog(user_id=user.id, workout_id=workout.id)
            db.session.add(log)
            db.session.flush()

            set_log = SetLog(
                workout_log_id=log.id,
                exercise_id=exercise.id,
                set_number=1,
                planned_reps=8,
                actual_reps=7,
                weight=225.0,
                completed=True
            )
            db.session.add(set_log)
            db.session.commit()

            data = set_log.to_dict()
            assert data['exercise_name'] == 'Bench Press'
            assert data['actual_reps'] == 7
            assert data['weight'] == 225.0


class TestWorkoutProgress:
    """Tests for tracking workout progress."""

    def test_progressive_weight_increase(self, app, user, exercise):
        """Test tracking weight increases over time."""
        with app.app_context():
            weights = [225.0, 230.0, 235.0, 240.0]
            
            for i, weight in enumerate(weights):
                log = WorkoutLog(user_id=user.id, custom_name=f'Session {i+1}')
                db.session.add(log)
                db.session.flush()

                set_log = SetLog(
                    workout_log_id=log.id,
                    exercise_id=exercise.id,
                    set_number=1,
                    weight=weight,
                    actual_reps=8
                )
                db.session.add(set_log)
            
            db.session.commit()

            # Query progression
            first_log = WorkoutLog.query.filter_by(user_id=user.id).order_by(WorkoutLog.started_at).first()
            last_log = WorkoutLog.query.filter_by(user_id=user.id).order_by(WorkoutLog.started_at.desc()).first()

            first_weight = first_log.sets.first().weight
            last_weight = last_log.sets.first().weight

            assert first_weight == 225.0
            assert last_weight == 240.0

    def test_rep_progression(self, app, user, exercise):
        """Test tracking rep increases."""
        with app.app_context():
            log1 = WorkoutLog(user_id=user.id, custom_name='Session 1')
            db.session.add(log1)
            db.session.flush()

            # First session: 6 reps
            set1 = SetLog(
                workout_log_id=log1.id,
                exercise_id=exercise.id,
                set_number=1,
                weight=225.0,
                actual_reps=6
            )
            db.session.add(set1)
            db.session.flush()

            log2 = WorkoutLog(user_id=user.id, custom_name='Session 2')
            db.session.add(log2)
            db.session.flush()

            # Second session: 8 reps (progress)
            set2 = SetLog(
                workout_log_id=log2.id,
                exercise_id=exercise.id,
                set_number=1,
                weight=225.0,
                actual_reps=8
            )
            db.session.add(set2)
            db.session.commit()

            # Verify progression
            logs = WorkoutLog.query.filter_by(user_id=user.id).order_by(WorkoutLog.started_at).all()
            assert logs[0].sets.first().actual_reps == 6
            assert logs[1].sets.first().actual_reps == 8
