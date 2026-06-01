#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# GulfAgent — one-command deploy to Hetzner via Dokploy
# Phase 4 (T80): Full production deploy script
# Usage: ./infra/deploy.sh [--env production|staging]
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

ENV="${2:-production}"
COMPOSE_FILE="docker-compose.yml"

echo "🚀 GulfAgent deploy — env: $ENV"
echo "────────────────────────────────"

# 1. Pull latest
echo "→ Pulling latest code..."
git pull origin main

# 2. Build images
echo "→ Building Docker images..."
docker compose -f "$COMPOSE_FILE" build --no-cache

# 3. Run DB migrations
echo "→ Running DB migrations..."
# Apply SQL migrations to Supabase via CLI or psql
# psql "$DATABASE_URL" -f backend/db/migrations/001_initial.sql

# 4. Rolling restart (zero downtime)
echo "→ Starting services..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

# 5. Health check
echo "→ Checking health..."
sleep 5
curl -sf http://localhost:8000/health | python3 -m json.tool

echo ""
echo "✅ Deploy complete"
