#!/bin/sh
set -e

uv run python manage.py migrate
uv run python manage.py collectstatic --no-input --clear
uv run python manage.py loaddata auth contenttypes subscription

exec "$@"
