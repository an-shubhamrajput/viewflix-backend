#!/usr/bin/env bash
set -euo pipefail

# Helper to run migrations for all models into migrations/
# Usage: ./scripts/migrate_all.sh "your message"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

export FLASK_APP=server.py
export MODEL_SCOPE=all
export MIGRATIONS_DIR=migrations

if [ ! -d "$MIGRATIONS_DIR" ]; then
  echo "Initializing migrations directory: $MIGRATIONS_DIR"
  flask db init
fi

MSG=${1:-"full schema migration"}
flask db migrate -m "$MSG"
flask db upgrade

echo "Done. All-model migrations applied to database defined in .env"


