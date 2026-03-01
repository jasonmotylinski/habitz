#!/usr/bin/env bash
cd /var/projects/habitz
source venv/bin/activate

python jobs/process_pending_recipes.py