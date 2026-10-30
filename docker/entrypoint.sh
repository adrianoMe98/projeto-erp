#!/bin/sh
set -eu

if [ "${DJANGO_AUTO_MIGRATE:-1}" = "1" ]; then
    python manage.py migrate --noinput
fi
python manage.py collectstatic --noinput

exec "$@"
