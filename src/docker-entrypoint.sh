#!/bin/bash
set -e


if [ "$1" = 'byro' ]; then
  su -p "${BYRO_USER}" -c "django-admin migrate"
  chown -R "${BYRO_USER}:${BYRO_USER}" /byro/data/*/*
  exec gunicorn --bind '[::]:80' --max-requests 1200 --max-requests-jitter 50 --log-level=info --worker-tmp-dir /dev/shm --workers "${GUNICORN_WORKERS:-3}" --user "${BYRO_USER}" --group "${BYRO_USER}" byro.wsgi
elif [ "$1" = 'django-admin' ]; then
  exec su -p "${BYRO_USER}" -c 'django-admin "$@"' -- "$@"
fi

exec "$@"
