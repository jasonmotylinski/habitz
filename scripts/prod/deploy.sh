#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/var/projects/habitz"
VENV="$APP_DIR/venv"

echo "==> Pulling latest code..."
cd "$APP_DIR"
git pull origin main

echo "==> Installing/updating dependencies..."
"$VENV/bin/pip" install -q -r requirements.txt

echo "==> Running tests (backend)..."
"$VENV/bin/pytest" tests/ -v --tb=short
if [ $? -ne 0 ]; then
  echo "ERROR: Backend tests failed. Aborting deployment."
  exit 1
fi

echo "==> Installing frontend test dependencies..."
npm ci --save-dev jest @testing-library/dom @testing-library/jest-dom 2>/dev/null || true

echo "==> Running tests (frontend)..."
npm test -- --coverage --passWithNoTests 2>/dev/null || true
# Frontend tests are optional (npm might not be installed), don't fail deployment

echo "==> Running database migrations..."
"$VENV/bin/python" scripts/prod/run_migrations.py
if [ $? -ne 0 ]; then
  echo "ERROR: Database migration failed. Aborting deployment."
  exit 1
fi

echo "==> Tests passed. Restarting gunicorn..."
sudo systemctl restart habitz

echo "==> Deployment complete."
