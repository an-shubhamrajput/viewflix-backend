#!/usr/bin/env bash
set -euo pipefail

# Helper to run admin-only migrations into migrations_admin/
# Usage: ./scripts/migrate_admin.sh "your message"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

export FLASK_APP=server.py
export MODEL_SCOPE=admin
export MIGRATIONS_DIR=migrations_admin

if [ ! -d "$MIGRATIONS_DIR" ]; then
  echo "Initializing migrations directory: $MIGRATIONS_DIR"
  flask db init
fi

MSG=${1:-"admin migration"}
flask db migrate -m "$MSG"
flask db upgrade

echo "Done. Admin migrations applied to database defined in .env"


