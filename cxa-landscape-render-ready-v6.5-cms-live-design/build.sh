#!/usr/bin/env bash
set -o errexit

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/build_public_assets.py
python scripts/static_audit.py
python -m compileall -q core project manage.py scripts
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py check --deploy
python manage.py collectstatic --noinput
