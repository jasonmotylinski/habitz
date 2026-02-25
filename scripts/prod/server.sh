#!/usr/bin/env bash
cd /var/projects/habitz
source venv/bin/activate
exec gunicorn --bind unix:/run/habitz.sock wsgi:application
