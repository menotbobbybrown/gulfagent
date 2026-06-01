#!/bin/bash
#
# GulfAgent startup script
# Runs Alembic migrations (non-fatal on error), then starts uvicorn
#

set -e

echo "==> Running Alembic migrations..."
alembic upgrade head && echo "==> Migrations complete." || echo "==> Migrations skipped (DB not available)."

echo "==> Starting uvicorn..."
exec "$@"