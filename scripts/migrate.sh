#!/usr/bin/env sh

set -e

DATABASE_URL="${DATABASE_URL:?DATABASE_URL must be set}"

echo "Installing yoyo..."
pip install --no-cache-dir yoyo-migrations psycopg2-binary

echo "Waiting for Postgres..."
until yoyo --batch list --database "$DATABASE_URL" /migrations >/dev/null 2>&1
do
  sleep 2
done

if [ "$1" = "mark" ]; then
  echo "Recording migrations as already applied (without running them)..."
  yoyo --batch -vv mark --database "$DATABASE_URL" /migrations
else
  echo "Applying migrations..."
  yoyo --batch -vv apply --database "$DATABASE_URL" /migrations
fi

echo "Migrations complete."
