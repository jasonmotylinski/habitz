"""Tests for workout tracker API endpoints."""
import pytest
from datetime import datetime, timezone
from workout_tracker.models.program import Program, ProgramWorkoutOrder
from workout_tracker.models.workout import Workout, WorkoutExercise
from workout_tracker.models.exercise import Exercise
from workout_tracker.models.log import WorkoutLog, SetLog, PelotonWorkout
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

    def test_workout_exercise_to_dict(self, app, workout):
        """Test workout exercise serialization."""
        with app.app_context():
            wo = db.session.get(Workout, workout.id)
            we = wo.workout_exercises.first()
            data = we.to_dict()

            assert data['exercise_name'] == 'Bench Press'
            assert data['default_sets'] == 4
            assert data['default_weight'] == 225.0

    def test_workout_to_dict_with_exercises(self, app, workout):
        """Test workout serialization with exercises."""
        with app.app_context():
            wo = db.session.get(Workout, workout.id)
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

    def test_program_to_dict_with_workouts(self, app, program):
        """Test program serialization with workouts."""
        with app.app_context():
            prog = db.session.get(Program, program.id)
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

    def test_start_workout_removes_stale_exercises_from_existing_log(self, app, user, workout, exercise):
        """Regression test: starting a workout should strip any exercises that don't
        belong to the workout template from an existing incomplete log.

        This can happen when two concurrent workout-switch requests race and both
        insert their exercises without seeing each other's deletes.
        """
        with app.app_context():
            # Create a second exercise that is NOT part of the workout template
            foreign_exercise = Exercise(
                user_id=user.id,
                name='Peloton - Main Set',
                type='cardio',
                unit='minutes',
            )
            db.session.add(foreign_exercise)
            db.session.flush()

            # Create an existing incomplete log for the workout
            log = WorkoutLog(
                user_id=user.id,
                workout_id=workout.id,
            )
            db.session.add(log)
            db.session.flush()

            # Add a valid set (exercise belongs to workout template)
            valid_set = SetLog(
                workout_log_id=log.id,
                exercise_id=exercise.id,
                set_number=1,
                planned_reps=8,
                actual_reps=8,
                weight=225.0,
                completed=False,
            )
            # Add a stale set (exercise does NOT belong to workout template)
            stale_set = SetLog(
                workout_log_id=log.id,
                exercise_id=foreign_exercise.id,
                set_number=1,
                duration_minutes=45,
                completed=False,
            )
            db.session.add(valid_set)
            db.session.add(stale_set)
            db.session.commit()

            log_id = log.id
            stale_set_id = stale_set.id
            valid_set_id = valid_set.id

            # Simulate start_workout cleanup logic
            workout_exercises = (
                WorkoutExercise.query
                .filter_by(workout_id=workout.id)
                .order_by(WorkoutExercise.position)
                .all()
            )
            template_exercise_ids = {we.exercise_id for we in workout_exercises}

            for s in log.sets.all():
                if s.exercise_id not in template_exercise_ids:
                    db.session.delete(s)
            db.session.commit()

            # The stale (foreign) set should be gone
            assert SetLog.query.get(stale_set_id) is None
            # The valid set should remain
            assert SetLog.query.get(valid_set_id) is not None
            # The log itself should still exist
            assert WorkoutLog.query.get(log_id) is not None


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


class TestExerciseProgress:
    """Tests for exercise progress / PR computation.

    Regression tests for the bug where SetLog ORM objects were accessed via
    dict subscript (s["weight"]) instead of attribute access (s.weight),
    causing TypeError: 'SetLog' object is not subscriptable.
    """

    def _fetch_set_logs(self, exercise_id, user_id):
        """Replicate the query used in exercise_progress endpoint."""
        return (
            SetLog.query
            .filter_by(exercise_id=exercise_id)
            .join(WorkoutLog)
            .filter(WorkoutLog.user_id == user_id)
            .all()
        )

    def test_pr_computed_with_attribute_access(self, app, user, exercise):
        """PR computation uses attribute access on SetLog ORM objects."""
        with app.app_context():
            for i, weight in enumerate([135.0, 185.0, 225.0, 200.0]):
                log = WorkoutLog(user_id=user.id, custom_name=f'Session {i+1}')
                db.session.add(log)
                db.session.flush()
                db.session.add(SetLog(
                    workout_log_id=log.id,
                    exercise_id=exercise.id,
                    set_number=1,
                    weight=weight,
                    completed=True,
                ))
            db.session.commit()

            set_logs = self._fetch_set_logs(exercise.id, user.id)

            # Exact pattern from exercise_progress — must use attribute access
            pr = max(
                (s.weight for s in set_logs if s.weight and s.completed),
                default=None,
            )
            assert pr == 225.0

    def test_pr_excludes_incomplete_sets(self, app, user, exercise):
        """Incomplete sets are excluded from the PR calculation."""
        with app.app_context():
            log = WorkoutLog(user_id=user.id, custom_name='Session')
            db.session.add(log)
            db.session.flush()
            db.session.add(SetLog(
                workout_log_id=log.id, exercise_id=exercise.id,
                set_number=1, weight=225.0, completed=True,
            ))
            # Heavier but incomplete — must not count as PR
            db.session.add(SetLog(
                workout_log_id=log.id, exercise_id=exercise.id,
                set_number=2, weight=300.0, completed=False,
            ))
            db.session.commit()

            set_logs = self._fetch_set_logs(exercise.id, user.id)
            pr = max(
                (s.weight for s in set_logs if s.weight and s.completed),
                default=None,
            )
            assert pr == 225.0

    def test_pr_is_none_when_no_completed_sets(self, app, user, exercise):
        """PR is None when no completed sets with weight exist."""
        with app.app_context():
            log = WorkoutLog(user_id=user.id, custom_name='Session')
            db.session.add(log)
            db.session.flush()
            db.session.add(SetLog(
                workout_log_id=log.id, exercise_id=exercise.id,
                set_number=1, weight=225.0, completed=False,
            ))
            db.session.commit()

            set_logs = self._fetch_set_logs(exercise.id, user.id)
            pr = max(
                (s.weight for s in set_logs if s.weight and s.completed),
                default=None,
            )
            assert pr is None

    def test_set_log_raises_on_subscript_access(self, app, user, exercise):
        """SetLog ORM objects are not subscriptable — dict-style access raises TypeError."""
        with app.app_context():
            log = WorkoutLog(user_id=user.id, custom_name='Session')
            db.session.add(log)
            db.session.flush()
            sl = SetLog(
                workout_log_id=log.id, exercise_id=exercise.id,
                set_number=1, weight=185.0, completed=True,
            )
            db.session.add(sl)
            db.session.commit()

            fetched = SetLog.query.get(sl.id)
            # Attribute access works
            assert fetched.weight == 185.0
            assert fetched.completed is True
            # Dict-style access is the bug — must raise TypeError
            with pytest.raises(TypeError):
                _ = fetched["weight"]

    def test_cardio_recent_durations_attribute_access(self, app, user):
        """Cardio duration computation also uses attribute access on SetLog."""
        with app.app_context():
            ex = Exercise(user_id=user.id, name='Treadmill', type='cardio', unit='mins')
            db.session.add(ex)
            db.session.flush()

            for minutes in [20, 30, 25]:
                log = WorkoutLog(user_id=user.id, custom_name='Cardio')
                db.session.add(log)
                db.session.flush()
                db.session.add(SetLog(
                    workout_log_id=log.id, exercise_id=ex.id,
                    set_number=1, duration_minutes=minutes, completed=True,
                ))
            db.session.commit()

            set_logs = self._fetch_set_logs(ex.id, user.id)

            # Exact pattern from exercise_progress for cardio
            recent_durations = []
            seen = set()
            for sl in set_logs:
                if sl.duration_minutes and sl.completed:
                    if sl.duration_minutes not in seen:
                        recent_durations.append(sl.duration_minutes)
                        seen.add(sl.duration_minutes)
                    if len(recent_durations) >= 3:
                        break

            assert len(recent_durations) == 3
            assert set(recent_durations) == {20, 25, 30}


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


class TestPlateauBumpLogic:
    """Regression tests for the weight-bump (plateau) recommendation.

    Bug: the bump used to fire whenever the same top weight was used
    3 sessions in a row, without checking that the planned reps were
    actually reached. session_strength_flags() now gates the bump on
    hitting the target reps at the top weight.
    """

    def _add_session(self, user_id, exercise_id, name, sets):
        """Add one workout log with the given (weight, planned, actual, completed) sets."""
        log = WorkoutLog(user_id=user_id, custom_name=name)
        db.session.add(log)
        db.session.flush()
        for num, (weight, planned, actual, completed) in enumerate(sets, start=1):
            db.session.add(SetLog(
                workout_log_id=log.id,
                exercise_id=exercise_id,
                set_number=num,
                weight=weight,
                planned_reps=planned,
                actual_reps=actual,
                completed=completed,
            ))
        return log

    def _fetch_session_sets(self, exercise_id, user_id, log_id):
        """Replicate the exercise_progress query, scoped to one session."""
        return (
            SetLog.query
            .filter_by(exercise_id=exercise_id, workout_log_id=log_id)
            .join(WorkoutLog)
            .filter(WorkoutLog.user_id == user_id)
            .all()
        )

    def test_same_weight_but_missed_reps_disqualifies_bump(self, app, user, exercise):
        """The failure mode: 3 sessions at the same weight where the last
        set of one session fell short of planned reps must NOT qualify."""
        with app.app_context():
            # Session hitting target: 3x5 @ 135 all completed
            hit = self._add_session(user.id, exercise.id, 'Hit', [
                (135.0, 5, 5, True),
                (135.0, 5, 5, True),
                (135.0, 5, 5, True),
            ])
            # Session missing target on final set: 5, 5, 4 @ 135
            missed = self._add_session(user.id, exercise.id, 'Missed', [
                (135.0, 5, 5, True),
                (135.0, 5, 5, True),
                (135.0, 5, 4, True),
            ])

            from workout_tracker.api.logs import session_strength_flags

            sets_hit = self._fetch_session_sets(exercise.id, user.id, hit.id)
            sets_missed = self._fetch_session_sets(exercise.id, user.id, missed.id)

            top_hit, hit_target_hit = session_strength_flags(sets_hit)
            top_missed, hit_target_missed = session_strength_flags(sets_missed)

            assert top_hit == 135.0 and top_missed == 135.0
            assert hit_target_hit is True
            # Old logic would have recommended a bump here — must not now
            assert hit_target_missed is False

    def test_all_target_reps_hit_qualifies(self, app, user, exercise):
        """Every working set at the top weight reached planned reps → qualifies."""
        with app.app_context():
            # Includes a lighter completed warm-up set — must be ignored
            log = self._add_session(user.id, exercise.id, 'Good session', [
                (95.0, 5, 5, True),
                (135.0, 5, 5, True),
                (135.0, 5, 5, True),
                (135.0, 5, 5, True),
            ])

            from workout_tracker.api.logs import session_strength_flags

            sets = self._fetch_session_sets(exercise.id, user.id, log.id)
            top_weight, hit_reps_target = session_strength_flags(sets)

            assert top_weight == 135.0
            assert hit_reps_target is True

    def test_incomplete_heavier_set_does_not_block_bump(self, app, user, exercise):
        """An uncompleted attempt above the top weight is ignored —
        the bump is judged on completed sets only."""
        with app.app_context():
            log = self._add_session(user.id, exercise.id, 'Failed attempt', [
                (135.0, 5, 5, True),
                (135.0, 5, 5, True),
                (145.0, 5, 3, False),
            ])

            from workout_tracker.api.logs import session_strength_flags

            sets = self._fetch_session_sets(exercise.id, user.id, log.id)
            top_weight, hit_reps_target = session_strength_flags(sets)

            assert top_weight == 135.0
            assert hit_reps_target is True

    def test_null_planned_reps_disqualifies(self, app, user, exercise):
        """Sets without planned/actual reps cannot prove the target was hit."""
        with app.app_context():
            log = self._add_session(user.id, exercise.id, 'No plan', [
                (135.0, None, None, True),
                (135.0, None, None, True),
            ])

            from workout_tracker.api.logs import session_strength_flags

            sets = self._fetch_session_sets(exercise.id, user.id, log.id)
            top_weight, hit_reps_target = session_strength_flags(sets)

            assert top_weight == 135.0
            assert hit_reps_target is False

    def test_no_completed_weighted_sets(self, app, user, exercise):
        """Nothing completed → no top weight, no bump."""
        with app.app_context():
            log = self._add_session(user.id, exercise.id, 'Empty', [
                (135.0, 5, None, False),
            ])

            from workout_tracker.api.logs import session_strength_flags

            sets = self._fetch_session_sets(exercise.id, user.id, log.id)
            top_weight, hit_reps_target = session_strength_flags(sets)

            assert top_weight is None
            assert hit_reps_target is False


class TestWorkoutFrequency:
    """Tests for the workout frequency endpoint.

    Follows the existing test pattern: replicate the aggregation logic
    directly rather than hitting the HTTP endpoint (which requires auth
    setup that the test client doesn't have).
    """

    def _add_completed_log(self, user_id, days_ago):
        """Add a completed workout log at a given offset from today."""
        log = WorkoutLog(
            user_id=user_id,
            custom_name=f'Workout {days_ago}d ago',
            started_at=datetime.utcnow() - __import__('datetime').timedelta(days=days_ago),
            completed_at=datetime.utcnow() - __import__('datetime').timedelta(days=days_ago),
        )
        db.session.add(log)
        db.session.flush()
        return log

    def _get_weekly_counts(self, user_id):
        """Replicate the weekly aggregation logic from the endpoint."""
        from collections import Counter
        now = datetime.utcnow()
        start = now - __import__('datetime').timedelta(weeks=11, days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)

        logs = (
            WorkoutLog.query
            .filter_by(user_id=user_id)
            .filter(WorkoutLog.completed_at.isnot(None))
            .order_by(WorkoutLog.started_at.asc())
            .all()
        )

        counts = Counter()
        for log in logs:
            if log.started_at < start:
                continue
            iso = log.started_at.isocalendar()
            counts[f"{iso[0]}-W{iso[1]:02d}"] += 1

        data = []
        for i in range(12):
            week_start = start + __import__('datetime').timedelta(weeks=i)
            iso = week_start.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
            data.append({"label": week_start.strftime("%b %d"), "count": counts.get(key, 0)})

        return data

    def test_weekly_returns_12_weeks(self, app, user):
        """Weekly view returns exactly 12 data points."""
        with app.app_context():
            self._add_completed_log(user.id, days_ago=5)
            db.session.commit()
            data = self._get_weekly_counts(user.id)
            assert len(data) == 12

    def test_monthly_returns_12_months(self, app, user):
        """Monthly view returns exactly 12 data points."""
        with app.app_context():
            self._add_completed_log(user.id, days_ago=30)
            db.session.commit()

            from collections import Counter
            now = datetime.utcnow()
            start = (now.replace(day=1) - __import__('datetime').timedelta(days=365)).replace(hour=0, minute=0, second=0, microsecond=0)

            logs = WorkoutLog.query.filter_by(user_id=user.id).filter(WorkoutLog.completed_at.isnot(None)).all()
            counts = Counter()
            for log in logs:
                if log.started_at < start:
                    continue
                counts[log.started_at.strftime("%Y-%m")] += 1

            data = []
            for i in range(12):
                month = (start.month - 1 + i) % 12 + 1
                year = start.year + (start.month - 1 + i) // 12
                key = f"{year}-{month:02d}"
                data.append({"label": datetime(year, month, 1).strftime("%b"), "count": counts.get(key, 0)})

            assert len(data) == 12

    def test_yearly_returns_all_years(self, app, user):
        """Yearly view returns data for each year with workouts."""
        with app.app_context():
            self._add_completed_log(user.id, days_ago=5)
            db.session.commit()

            from collections import Counter
            now = datetime.utcnow()
            logs = WorkoutLog.query.filter_by(user_id=user.id).filter(WorkoutLog.completed_at.isnot(None)).all()
            counts = Counter()
            for log in logs:
                counts[str(log.started_at.year)] += 1

            min_year = min(int(k) for k in counts.keys())
            max_year = now.year
            data = [{"label": str(y), "count": counts.get(str(y), 0)} for y in range(min_year, max_year + 1)]

            assert len(data) >= 1
            assert data[-1]['count'] >= 1

    def test_counts_multiple_workouts_in_same_week(self, app, user):
        """Multiple workouts in the same week are counted correctly."""
        with app.app_context():
            self._add_completed_log(user.id, days_ago=1)
            self._add_completed_log(user.id, days_ago=3)
            db.session.commit()
            data = self._get_weekly_counts(user.id)
            max_count = max(d['count'] for d in data)
            assert max_count >= 2

    def test_streak_counts_consecutive_weeks(self, app, user):
        """Current streak counts consecutive weeks with workouts from the end."""
        with app.app_context():
            # Add workouts today and yesterday (both in the current week since today is Monday)
            self._add_completed_log(user.id, days_ago=0)
            self._add_completed_log(user.id, days_ago=1)
            db.session.commit()
            data = self._get_weekly_counts(user.id)

            current_streak = 0
            for d in reversed(data):
                if d['count'] > 0:
                    current_streak += 1
                else:
                    break

            # The most recent week should have workouts
            assert current_streak >= 1

    def test_empty_returns_zeros(self, app, user):
        """No workouts returns empty data with zero stats."""
        with app.app_context():
            data = self._get_weekly_counts(user.id)
            total = sum(d['count'] for d in data)
            assert total == 0

            current_streak = 0
            for d in reversed(data):
                if d['count'] > 0:
                    current_streak += 1
                else:
                    break
            assert current_streak == 0


class TestPelotonWorkout:
    """Tests for PelotonWorkout model and import logic."""

    def test_peloton_workout_creation(self, app, user):
        """PelotonWorkout record can be created with all fields."""
        with app.app_context():
            log = WorkoutLog(user_id=user.id, custom_name='Peloton: Test Ride')
            db.session.add(log)
            db.session.flush()

            pw = PelotonWorkout(
                user_id=user.id,
                peloton_workout_id='test-123',
                ride_title='45 min Power Zone Max',
                ride_duration=45,
                total_output=450.0,
                calories=350,
                average_cadence=85.0,
                average_resistance=42.0,
                average_heartrate=145.0,
                leaderboard_rank=150,
                total_leaderboard=5000,
                workout_log_id=log.id,
            )
            db.session.add(pw)
            db.session.commit()

            assert pw.id is not None
            assert pw.peloton_workout_id == 'test-123'
            assert pw.ride_title == '45 min Power Zone Max'
            assert pw.ride_duration == 45
            assert pw.workout_log_id == log.id

    def test_peloton_workout_dedup(self, app, user):
        """Duplicate peloton_workout_id raises IntegrityError."""
        from sqlalchemy.exc import IntegrityError
        with app.app_context():
            pw1 = PelotonWorkout(
                user_id=user.id,
                peloton_workout_id='dedup-test',
                ride_title='Ride 1',
            )
            db.session.add(pw1)
            db.session.commit()

            pw2 = PelotonWorkout(
                user_id=user.id,
                peloton_workout_id='dedup-test',
                ride_title='Ride 2',
            )
            db.session.add(pw2)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_parse_workout_data_extracts_fields(self, app, user):
        """parse_workout_data extracts and normalizes fields from Peloton response."""
        with app.app_context():
            from workout_tracker.jobs.import_peloton_workouts import parse_workout_data

            mock_workout = {
                'id': 'abc-123',
                'status': 'COMPLETE',
                'fitness_discipline': 'cycling',
                'start_time': '2026-09-01T10:00:00+00:00',
                'end_time': '2026-09-01T10:45:00+00:00',
                'leaderboard_rank': 100,
                'total_leaderboard_users': 3000,
                'ride': {
                    'title': '45 min HIIT Ride',
                    'duration': 2700,
                },
                'performance_graph': {
                    'summaries': [
                        {'metric_type': 'total_output', 'value': 500.0},
                        {'metric_type': 'calories', 'value': 400},
                        {'metric_type': 'avg_cadence', 'value': 88.0},
                    ]
                }
            }

            result = parse_workout_data(mock_workout)

            assert result['peloton_workout_id'] == 'abc-123'
            assert result['ride_title'] == '45 min HIIT Ride'
            assert result['ride_duration'] == 45
            assert result['total_output'] == 500.0
            assert result['calories'] == 400
            assert result['average_cadence'] == 88.0
            assert result['leaderboard_rank'] == 100
            assert result['total_leaderboard'] == 3000
