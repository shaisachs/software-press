#!/usr/bin/env bash
# Run unit tests for both services inside Docker containers, so no local
# Python toolchain is required.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

status=0

test_in_docker() {
  local name="$1"
  local tests_dir="$2"
  local image="software-press-tests-$name"

  echo "==> $name: building test image"
  docker build -q -t "$image" -f - "$ROOT/services/$name" <<'DOCKERFILE'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pytest
COPY . .
DOCKERFILE

  echo "==> $name: running tests"
  docker run --rm -w /app "$image" python3 -m pytest "$tests_dir" -q || status=1
}

test_in_docker agent tests
test_in_docker api tests/unit

exit $status
