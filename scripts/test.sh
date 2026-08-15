#!/usr/bin/env bash
# Run unit tests for both services without a Docker build.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

REQUIRED="pytest fastapi pydantic httpx psycopg2 redis"

missing=""
for mod in $REQUIRED; do
  if ! python3 -c "import $mod" >/dev/null 2>&1; then
    missing="$missing $mod"
  fi
done

if [ -n "$missing" ]; then
  echo "Installing missing test dependencies:$missing"
  python3 -m pip install --user --break-system-packages $missing
fi

status=0

echo "==> agent"
(cd "$ROOT/services/agent" && python3 -m pytest tests -q) || status=1

echo "==> api"
(cd "$ROOT/services/api" && python3 -m pytest tests -q) || status=1

exit $status
