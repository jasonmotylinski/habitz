#!/usr/bin/env bash
cd /var/projects/habitz
source venv/bin/activate

python meal_planner/jobs/process_pending_recipes.py