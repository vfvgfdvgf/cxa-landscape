#!/usr/bin/env bash
set -o errexit

python manage.py migrate --noinput
python manage.py ensure_admin_user
python manage.py ensure_public_catalog || echo "WARNING: public catalogue sync failed; serving existing data."

if [ "${DJANGO_BOOTSTRAP_ON_START:-False}" = "True" ]; then
  python manage.py bootstrap_nakheel_najd
fi

exec gunicorn project.wsgi:application \
  --bind "0.0.0.0:${PORT:-10000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout 120 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile -
