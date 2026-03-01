#!/usr/bin/env python3
"""
Run Flask-Migrate database migrations for the landing app.

Bypasses the Flask CLI (which fails to auto-detect the correct app in
the multi-app wsgi.py), instead importing landing_app directly.

Usage: python scripts/prod/run_migrations.py
"""
import sys
import os

# Ensure the habitz package root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from landing import create_app
from flask_migrate import upgrade

app = create_app()
with app.app_context():
    upgrade()
    print("✓ Migrations applied successfully")
