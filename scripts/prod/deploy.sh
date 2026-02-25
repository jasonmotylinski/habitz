#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/var/projects/habitz"
VENV="$APP_DIR/venv"

echo "==> Pulling latest code..."
cd "$APP_DIR"
git pull origin main

echo "==> Installing/updating dependencies..."
"$VENV/bin/pip" install -q -r requirements.txt

echo "==> Restarting gunicorn..."
sudo systemctl restart habitz

echo "==> Done."
