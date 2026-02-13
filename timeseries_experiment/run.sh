#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DB_CONTAINER_NAME="${DB_CONTAINER_NAME:-ts-pg}"
DB_NAME="${DB_NAME:-timeseries_lab}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_PORT="${DB_PORT:-5432}"
POSTGRES_IMAGE="${POSTGRES_IMAGE:-postgres:16}"

SERIES_COUNT="${SERIES_COUNT:-1000}"
POINTS_PER_SERIES="${POINTS_PER_SERIES:-1440}"
STEP_SECONDS="${STEP_SECONDS:-10}"
JSON_OUT="${JSON_OUT:-experiments/results.json}"

DATABASE_URL_DEFAULT="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${DB_PORT}/${DB_NAME}"
DATABASE_URL="${DATABASE_URL:-$DATABASE_URL_DEFAULT}"

ensure_container() {
  if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER_NAME}$"; then
    echo "Postgres container '${DB_CONTAINER_NAME}' is already running."
    return
  fi

  if docker ps -a --format '{{.Names}}' | grep -q "^${DB_CONTAINER_NAME}$"; then
    echo "Starting existing container '${DB_CONTAINER_NAME}'..."
    docker start "${DB_CONTAINER_NAME}" >/dev/null
    return
  fi

  echo "Creating and starting container '${DB_CONTAINER_NAME}'..."
  docker run --name "${DB_CONTAINER_NAME}" \
    -e POSTGRES_PASSWORD="${DB_PASSWORD}" \
    -e POSTGRES_DB="${DB_NAME}" \
    -p "${DB_PORT}:5432" \
    -d "${POSTGRES_IMAGE}" >/dev/null
}

wait_for_postgres() {
  echo "Waiting for PostgreSQL to accept connections..."
  for _ in {1..30}; do
    if docker exec "${DB_CONTAINER_NAME}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
      echo "PostgreSQL is ready."
      return
    fi
    sleep 1
  done
  echo "PostgreSQL did not become ready in time." >&2
  exit 1
}

ensure_venv() {
  if [[ ! -d ".venv" ]]; then
    echo "Creating local venv..."
    python3 -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -r experiments/requirements.txt >/dev/null
}

ensure_container
wait_for_postgres
ensure_venv

echo "Running experiments with:"
echo "  DATABASE_URL=${DATABASE_URL}"
echo "  SERIES_COUNT=${SERIES_COUNT}"
echo "  POINTS_PER_SERIES=${POINTS_PER_SERIES}"
echo "  STEP_SECONDS=${STEP_SECONDS}"
echo "  JSON_OUT=${JSON_OUT}"

python experiments/run_experiments.py \
  --database-url "${DATABASE_URL}" \
  --series-count "${SERIES_COUNT}" \
  --points-per-series "${POINTS_PER_SERIES}" \
  --step-seconds "${STEP_SECONDS}" \
  --json-out "${JSON_OUT}"

