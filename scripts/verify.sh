#!/usr/bin/env bash
set -euo pipefail

python scripts/build_public_assets.py
python scripts/static_audit.py
python -m compileall -q core project manage.py scripts/static_audit.py
node --check static/js/site-v4-4.js
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py sync_fixed_locations
python manage.py test --verbosity 2
python manage.py collectstatic --noinput

echo "All project verification checks passed."
