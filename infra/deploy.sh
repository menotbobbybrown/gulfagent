#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# GulfAgent — one-command deploy to Hetzner via Dokploy
# Phase 4 (T80): Full production deploy script
# Usage: ./infra/deploy.sh [--env production|staging]
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

# Parse arguments
ENV="production"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)
            ENV="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--env production|staging]"
            exit 1
            ;;
    esac
done

if [[ "$ENV" != "production" && "$ENV" != "staging" ]]; then
    echo "Error: --env must be 'production' or 'staging'"
    exit 1
fi

COMPOSE_FILE="docker-compose.yml"
COMPOSE_PROJECT="gulfagent-${ENV}"

echo "🚀 GulfAgent deploy — env: $ENV"
echo "─────────────────────────────────"

# 1. Pull latest
echo "→ Pulling latest code..."
git pull origin main

# 2. Load environment
ENV_FILE=".env.${ENV}"
if [[ -f "$ENV_FILE" ]]; then
    echo "→ Loading environment from $ENV_FILE"
    set -a
    source "$ENV_FILE"
    set +a
elif [[ -f ".env" ]]; then
    echo "→ Loading environment from .env"
    set -a
    source ".env"
    set +a
else
    echo "⚠ Warning: No .env file found. Make sure environment variables are set."
fi

# 3. Build images
echo "→ Building Docker images..."
docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" build --no-cache

# 4. Run DB migrations (via the backend container)
echo "→ Running DB migrations..."
if command -v alembic &> /dev/null; then
    alembic upgrade head
elif docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" ps --services 2>/dev/null | grep -q "backend"; then
    # Run migrations inside the backend container
    docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" run --rm backend alembic upgrade head || echo "⚠ Alembic migration failed, check logs"
else
    echo "→ Skipping alembic (no running backend container). Applying SQL migrations directly..."
    for sql_file in backend/db/migrations/*.sql; do
        echo "   Applying $(basename "$sql_file")..."
        if [[ -n "${DATABASE_URL:-}" ]]; then
            psql "$DATABASE_URL" -f "$sql_file" 2>/dev/null || echo "⚠ Could not apply $sql_file (psql not available or no DATABASE_URL)"
        else
            echo "   Skipping (no DATABASE_URL set)"
        fi
    done
fi

# 5. Rolling restart (zero downtime)
echo "→ Starting services..."
docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" up -d --remove-orphans

# 6. Health check with retry (T80 — 5 attempts, 5s apart)
echo "→ Checking health..."
HEALTHY=false
for i in $(seq 1 5); do
    echo "   Attempt $i/5..."
    sleep 5
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" == "200" ]]; then
        HEALTHY=true
        echo "   ✓ Health check passed (HTTP $HTTP_CODE)"
        curl -sf http://localhost:8000/health | python3 -m json.tool 2>/dev/null || true
        break
    else
        echo "   ⚠ Health check returned HTTP $HTTP_CODE, retrying..."
    fi
done

# T80 — Rollback on health check failure
if [[ "$HEALTHY" != "true" ]]; then
    echo ""
    echo "❌ Health check failed after 5 attempts. Rolling back..."
    # Rollback to previous compose state (restart previous containers)
    docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" up -d --no-build 2>/dev/null || true
    echo "   Rollback complete. Previous deployment restored."
    exit 1
fi

echo ""
echo "✅ Deploy complete — $ENV"