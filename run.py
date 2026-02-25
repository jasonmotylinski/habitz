"""Development server — runs all apps via DispatcherMiddleware on a single port."""
import os
from werkzeug.serving import run_simple
from wsgi import application

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    run_simple('0.0.0.0', port, application, use_reloader=True, use_debugger=True)
