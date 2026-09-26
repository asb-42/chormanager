#!/bin/sh
# M5 entrypoint: migrate, then serve. Fails fast when the DB is down.
set -e
alembic -c alembic.ini upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
