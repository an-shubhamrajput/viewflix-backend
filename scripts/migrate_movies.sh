#!/usr/bin/env bash
set -euo pipefail

# Helper to run movies-only migrations into migrations_movies/
# Usage: ./scripts/migrate_movies.sh "your message"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

export FLASK_APP=server.py
export MODEL_SCOPE=movies
export MIGRATIONS_DIR=migrations_movies

if [ ! -d "$MIGRATIONS_DIR" ]; then
  echo "Initializing migrations directory: $MIGRATIONS_DIR"
  flask db init
fi

MSG=${1:-"movies migration"}
flask db migrate -m "$MSG"
flask db upgrade

echo "Done. Movies migrations applied to database defined in .env"


