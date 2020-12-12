#!/bin/bash
set -e


if [ "$1" = 'byro' ]; then
  su -p uid1000 -c "django-admin migrate"
  exec gunicorn --bind '[::]:80' --max-requests 1200 --max-requests-jitter 50 --log-level=info --worker-tmp-dir /dev/shm --workers "${GUNICORN_WORKERS:-3}" --user uid1000 --group uid1000 byro.wsgi
elif [ "$1" = 'django-admin' ]; then
  exec su -p uid1000 -c 'django-admin "$@"' -- "$@"
fi

exec "$@"
