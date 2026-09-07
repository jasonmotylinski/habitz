#!/usr/bin/env python3
"""
Cron job: Import completed Peloton workouts into Habitz

Usage: python workout_tracker/jobs/import_peloton_workouts.py
Add to crontab: 0 6 * * * cd /var/projects/habitz && venv/bin/python workout_tracker/jobs/import_peloton_workouts.py

This script:
1. Authenticates with Peloton via pylotoncycle
2. Fetches recent completed cycling workouts
3. Creates WorkoutLog + SetLog records for new rides
4. Stores rich metrics in peloton_workouts table
5. Deduplicates via peloton_workout_id (unique)
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/peloton_import.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add the habitz package root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env before create_app() so os.environ has PELOTON_USERNAME etc.
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

try:
    from workout_tracker import create_app
    from workout_tracker.models.log import WorkoutLog, SetLog, PelotonWorkout
    from workout_tracker.models.workout import Workout, WorkoutExercise
    from workout_tracker.models.exercise import Exercise
    from shared import db
    from shared.user import User

    # Import all models that User has relationships to
    import calorie_tracker.models  # noqa: F401
    import fasting_tracker.models  # noqa: F401
    import meal_planner.models  # noqa: F401
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)


def fetch_peloton_workouts(num_workouts=10):
    """
    Fetch recent completed cycling workouts from Peloton.

    Returns list of dicts with workout data, or empty list on failure.
    """
    try:
        from pylotoncycle import PylotonCycle

        username = os.environ.get('PELOTON_USERNAME')
        password = os.environ.get('PELOTON_PASSWORD')

        if not username or not password:
            logger.error("PELOTON_USERNAME or PELOTON_PASSWORD not set in environment")
            return []

        logger.info("Authenticating with Peloton...")
        conn = PylotonCycle(username=username, password=password)

        logger.info(f"Fetching last {num_workouts} workouts...")
        workouts = conn.GetRecentWorkouts(num_workouts)

        # Filter to completed cycling workouts only
        cycling_workouts = []
        for w in workouts:
            if w.get('status') != 'COMPLETE':
                continue
            if w.get('fitness_discipline') != 'cycling':
                continue
            cycling_workouts.append(w)

        logger.info(f"Found {len(cycling_workouts)} completed cycling workouts")
        return cycling_workouts

    except Exception as e:
        logger.error(f"Error fetching Peloton workouts: {e}")
        return []


def parse_workout_data(workout):
    """
    Extract relevant fields from a pylotoncycle workout dict.

    Returns dict with normalized field names.
    """
    ride = workout.get('ride', {})

    # Get metrics from performance_graph if available
    perf = workout.get('performance_graph', {})
    summaries = perf.get('summaries', [])

    # Extract totals from summaries
    total_output = None
    calories = None
    average_cadence = None
    average_resistance = None
    average_heartrate = None

    for summary in summaries:
        if summary.get('metric_type') == 'total_output':
            total_output = summary.get('value')
        elif summary.get('metric_type') == 'calories':
            calories = summary.get('value')
        elif summary.get('metric_type') == 'avg_cadence':
            average_cadence = summary.get('value')
        elif summary.get('metric_type') == 'avg_resistance':
            average_resistance = summary.get('value')
        elif summary.get('metric_type') == 'avg_heart_rate':
            average_heartrate = summary.get('value')

    # Fallback to top-level fields if summaries didn't have it
    if total_output is None:
        total_output = workout.get('total_output')
    if calories is None:
        calories = workout.get('calories')
    if average_cadence is None:
        average_cadence = workout.get('average_cadence')
    if average_resistance is None:
        average_resistance = workout.get('average_resistance')
    if average_heartrate is None:
        average_heartrate = workout.get('average_heartrate')

    # Duration from ride (seconds) or workout
    duration_seconds = ride.get('duration') or workout.get('duration')
    duration_minutes = duration_seconds // 60 if duration_seconds else None

    return {
        'peloton_workout_id': workout.get('id'),
        'ride_title': ride.get('title', 'Peloton Ride'),
        'ride_duration': duration_minutes,
        'total_output': total_output,
        'calories': calories,
        'average_cadence': average_cadence,
        'average_resistance': average_resistance,
        'average_heartrate': average_heartrate,
        'leaderboard_rank': workout.get('leaderboard_rank'),
        'total_leaderboard': workout.get('total_leaderboard_users'),
        'started_at': workout.get('start_time'),
        'ended_at': workout.get('end_time'),
    }


def _parse_peloton_timestamp(ts):
    """Convert Peloton timestamp (Unix epoch or ISO string) to datetime."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return datetime.utcfromtimestamp(ts)
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    return ts


def import_workout(user_id, data, cardio_workout, main_set_exercise):
    """
    Import a single Peloton workout into Habitz.

    Creates WorkoutLog + SetLog + PelotonWorkout records.
    Returns the created PelotonWorkout, or None on failure.
    """
    # Parse timestamps (Peloton returns Unix epochs)
    started_at = _parse_peloton_timestamp(data['started_at'])
    ended_at = _parse_peloton_timestamp(data['ended_at'])

    # Create WorkoutLog
    log = WorkoutLog(
        user_id=user_id,
        workout_id=cardio_workout.id if cardio_workout else None,
        custom_name=f"Peloton: {data['ride_title']}" if not cardio_workout else None,
        started_at=started_at or datetime.utcnow(),
        completed_at=ended_at or datetime.utcnow(),
    )
    db.session.add(log)
    db.session.flush()

    # Create SetLog for the ride
    set_log = SetLog(
        workout_log_id=log.id,
        exercise_id=main_set_exercise.id,
        set_number=1,
        duration_minutes=data['ride_duration'],
        completed=True,
    )
    db.session.add(set_log)

    # Create PelotonWorkout record
    peloton_record = PelotonWorkout(
        user_id=user_id,
        peloton_workout_id=data['peloton_workout_id'],
        ride_title=data['ride_title'],
        ride_duration=data['ride_duration'],
        total_output=data['total_output'],
        calories=data['calories'],
        average_cadence=data['average_cadence'],
        average_resistance=data['average_resistance'],
        average_heartrate=data['average_heartrate'],
        leaderboard_rank=data['leaderboard_rank'],
        total_leaderboard=data['total_leaderboard'],
        workout_log_id=log.id,
    )
    db.session.add(peloton_record)

    return peloton_record


def find_or_create_cardio_exercise(user_id):
    """Find or create the Peloton main set exercise for this user."""
    exercise = Exercise.query.filter_by(
        user_id=user_id,
        name='Peloton - Main set',
        type='cardio',
    ).first()

    if not exercise:
        exercise = Exercise(
            user_id=user_id,
            name='Peloton - Main set',
            type='cardio',
            unit='mins',
        )
        db.session.add(exercise)
        db.session.flush()

    return exercise


def find_or_create_cardio_workout(user_id):
    """Find or create a Cardio workout template for this user."""
    workout = Workout.query.filter_by(
        user_id=user_id,
        name='Cardio',
    ).first()

    return workout  # May be None — that's OK, WorkoutLog.workout_id is nullable


def process_peloton_imports(num_workouts=50):
    """Main function to import Peloton workouts."""

    app = create_app('production')

    with app.app_context():
        username = os.environ.get('PELOTON_USERNAME')
        password = os.environ.get('PELOTON_PASSWORD')

        if not username or not password:
            logger.error("PELOTON_USERNAME/PELOTON_PASSWORD not configured")
            return False

        # Get the user (Jason — single user for now)
        user = User.query.filter_by(username='Jason').first()
        if not user:
            logger.error("User 'Jason' not found")
            return False

        # Fetch workouts from Peloton
        workouts = fetch_peloton_workouts(num_workouts)
        if not workouts:
            logger.info("No workouts to import")
            return True

        # Find or create exercise and workout template
        main_set_exercise = find_or_create_cardio_exercise(user.id)
        cardio_workout = find_or_create_cardio_workout(user.id)

        imported = 0
        skipped = 0
        failed = 0

        for workout in workouts:
            try:
                data = parse_workout_data(workout)

                # Dedup check
                existing = PelotonWorkout.query.filter_by(
                    peloton_workout_id=data['peloton_workout_id']
                ).first()

                if existing:
                    skipped += 1
                    continue

                # Import
                peloton_record = import_workout(
                    user.id, data, cardio_workout, main_set_exercise
                )
                imported += 1
                logger.info(f"  Imported: {data['ride_title']} ({data['ride_duration']} min)")

            except Exception as e:
                logger.error(f"Error importing workout: {e}")
                failed += 1

        db.session.commit()

        logger.info(f"Import complete: {imported} imported, {skipped} skipped, {failed} failed")
        return True


if __name__ == '__main__':
    try:
        # Default to 50 for first run (backfill ~90 days), use --recent for 10
        num = 50
        if '--recent' in sys.argv:
            num = 10

        success = process_peloton_imports(num_workouts=num)
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
