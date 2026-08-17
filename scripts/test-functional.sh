#!/usr/bin/env bash
# Run the functional test suite against "real" throwaway dependencies.
#
# Stands up throwaway Postgres and Redis containers, applies all migrations
# (via the same scripts/migrate.sh path used in production), boots the real API,
# and runs the Karate suite in services/api/tests/functional against it. The Karate
# scenarios assert row-level state directly against Postgres (JDBC) and verify
# queue membership directly against Redis (jedis).
#
# Exits non-zero if the API fails to come up or any functional test fails, so
# it can be used as a gate at the orchestration layer (e.g. a CI job that must
# pass before the API image is built/pushed).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT/docker-compose.functional.yaml"
PROJECT="software-press-functional"
API_CONTAINER="sp-test-api"

cleanup() {
  docker compose -p "$PROJECT" -f "$COMPOSE_FILE" down -v
}
trap cleanup EXIT

echo "==> Starting throwaway Postgres, Redis, migrations, and API"
docker compose -p "$PROJECT" -f "$COMPOSE_FILE" up -d --build \
  postgres-test redis-test db-migrate-test api-test

echo "==> Waiting for api-test to become healthy"
status=""
for _ in $(seq 1 60); do
  status="$(docker inspect -f '{{.State.Health.Status}}' "$API_CONTAINER" 2>/dev/null || true)"
  if [ "$status" = "healthy" ]; then
    break
  fi
  sleep 2
done
if [ "$status" != "healthy" ]; then
  echo "error: api-test did not become healthy" >&2
  docker compose -p "$PROJECT" -f "$COMPOSE_FILE" logs --no-color >&2 || true
  exit 1
fi

echo "==> Running Karate functional suite"
status=0
docker compose -p "$PROJECT" -f "$COMPOSE_FILE" run --rm -T --build karate-runner || status=$?

if [ "$status" -ne 0 ]; then
  echo "==> Functional test suite FAILED (exit $status)" >&2
  docker compose -p "$PROJECT" -f "$COMPOSE_FILE" logs --no-color >&2 || true
  exit "$status"
fi

echo "==> Functional tests passed."
