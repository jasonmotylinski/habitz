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

# All apps share one session cookie at path '/' so login at the landing app
# is recognised by every sub-app.  They all use the same SECRET_KEY from .env.
_here = os.path.dirname(os.path.abspath(__file__))
_shared_session = dict(
    SESSION_COOKIE_NAME='habitz_session',
    SESSION_COOKIE_PATH='/',
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_NAME='habitz_remember',
    REMEMBER_COOKIE_PATH='/',
)

meal_planner_app.config.update(
    **_shared_session,
    # Use an absolute upload path so it doesn't depend on CWD
    UPLOAD_FOLDER=os.environ.get(
        'MEAL_PLANNER_UPLOAD_FOLDER',
        os.path.join(_here, 'uploads'),
    ),
)
calorie_tracker_app.config.update(**_shared_session)
fasting_tracker_app.config.update(**_shared_session)
workout_tracker_app.config.update(**_shared_session)

application = DispatcherMiddleware(landing_app, {
    '/meals': meal_planner_app,
    '/calories': calorie_tracker_app,
    '/fasting': fasting_tracker_app,
    '/workouts': workout_tracker_app,
})

# Trust X-Forwarded-Proto / X-Forwarded-Host from a reverse proxy (nginx)
application = ProxyFix(application, x_proto=1, x_host=1)
