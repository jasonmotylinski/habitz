"""
Habitz — unified WSGI entry point.

Mounts all four trackers under sub-paths using Werkzeug's DispatcherMiddleware
so a single gunicorn process serves everything.

URL map:
  /           → landing page
  /meals/     → meal planner
  /calories/  → calorie tracker
  /fasting/   → fasting tracker
  /workouts/  → workout tracker
"""
import os

# All apps share a single database in habitz/habitz/instance/habitz.db
_here = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(_here, 'instance'), exist_ok=True)

from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.middleware.proxy_fix import ProxyFix

from landing import create_app as create_landing
from meal_planner import create_app as create_meal_planner
from calorie_tracker import create_app as create_calorie_tracker
from fasting_tracker import create_app as create_fasting_tracker
from workout_tracker import create_app as create_workout_tracker

env = os.environ.get('FLASK_ENV', 'production')

landing_app = create_landing()
meal_planner_app = create_meal_planner(env)
calorie_tracker_app = create_calorie_tracker(env)
fasting_tracker_app = create_fasting_tracker(env)
workout_tracker_app = create_workout_tracker(env)

# Each sub-app needs its own session cookie scoped to its path prefix,
# otherwise cookies from different apps would overwrite each other.
_here = os.path.dirname(os.path.abspath(__file__))
meal_planner_app.config.update(
    SESSION_COOKIE_NAME='habitz_meals_session',
    SESSION_COOKIE_PATH='/meals',
    REMEMBER_COOKIE_NAME='habitz_meals_remember',
    REMEMBER_COOKIE_PATH='/meals',
    # Use an absolute upload path so it doesn't depend on CWD
    UPLOAD_FOLDER=os.environ.get(
        'MEAL_PLANNER_UPLOAD_FOLDER',
        os.path.join(_here, 'uploads'),
    ),
)

calorie_tracker_app.config.update(
    SESSION_COOKIE_NAME='habitz_calories_session',
    SESSION_COOKIE_PATH='/calories',
    REMEMBER_COOKIE_NAME='habitz_calories_remember',
    REMEMBER_COOKIE_PATH='/calories',
)

fasting_tracker_app.config.update(
    SESSION_COOKIE_NAME='habitz_fasting_session',
    SESSION_COOKIE_PATH='/fasting',
    REMEMBER_COOKIE_NAME='habitz_fasting_remember',
    REMEMBER_COOKIE_PATH='/fasting',
)

workout_tracker_app.config.update(
    SESSION_COOKIE_NAME='habitz_workouts_session',
    SESSION_COOKIE_PATH='/workouts',
    REMEMBER_COOKIE_NAME='habitz_workouts_remember',
    REMEMBER_COOKIE_PATH='/workouts',
)

application = DispatcherMiddleware(landing_app, {
    '/meals': meal_planner_app,
    '/calories': calorie_tracker_app,
    '/fasting': fasting_tracker_app,
    '/workouts': workout_tracker_app,
})

# Trust X-Forwarded-Proto / X-Forwarded-Host from a reverse proxy (nginx)
application = ProxyFix(application, x_proto=1, x_host=1)
