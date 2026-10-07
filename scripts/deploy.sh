#!/usr/bin/env bash
# Local deployment pipeline: test -> build -> deploy -> health check -> rollback.
#
# This is the single entrypoint used by:
#   - `make deploy`
#   - the git hooks in .githooks/ (auto-deploy on commit / merge)
#   - the CI workflow (test + build stages only, see .github/workflows/pipeline.yml)
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

IMAGE="blog-app"
SHA="$(git rev-parse --short HEAD 2>/dev/null || echo nogit)"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$ROOT/.pipeline"
LOG="$LOG_DIR/deploy-$RUN_ID.log"
LOCK="$LOG_DIR/deploy.lock"
HEALTH_URL="http://127.0.0.1:5055/health"
HEALTH_TIMEOUT=90

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG") 2>&1

log() { printf '[pipeline %s] %s\n' "$(date +%H:%M:%S)" "$*"; }

# ---------- single-flight lock ----------
if [ -f "$LOCK" ]; then
  other="$(cat "$LOCK" 2>/dev/null || true)"
  if [ -n "${other:-}" ] && kill -0 "$other" 2>/dev/null; then
    log "another deploy is already running (pid $other) — skipping this run"
    exit 0
  fi
fi
echo $$ >"$LOCK"
trap 'rm -f "$LOCK"' EXIT

log "deploy $RUN_ID starting (git $SHA)"
log ".env present: $([ -f .env ] && echo yes || echo 'NO — copy .env.example to .env')"

# ---------- stage 1: build ----------
log "stage 1/5 — building $IMAGE:$SHA"
export APP_VERSION="$SHA"
if docker image inspect "$IMAGE:latest" >/dev/null 2>&1; then
  docker tag "$IMAGE:latest" "$IMAGE:previous"
  log "saved rollback image as $IMAGE:previous"
fi
docker build -q --target runtime -t "$IMAGE:latest" -t "$IMAGE:$SHA" --build-arg APP_VERSION="$SHA" . >/dev/null

# ---------- stage 2: test ----------
log "stage 2/5 — running tests with the configured Supabase environment"
docker build -q --target test -t "$IMAGE:test" --build-arg APP_VERSION="$SHA" . >/dev/null
docker run --rm --env-file .env -e APP_VERSION="$SHA" "$IMAGE:test" \
  python -m pytest -q test_app.py -p no:cacheprovider

# ---------- stage 3: dependencies ----------
log "stage 3/5 — starting observability stack"
docker compose up -d --remove-orphans \
  prometheus alertmanager alertauth alert-webhook loki promtail node-exporter blackbox grafana

# ---------- stage 4: app ----------
log "stage 4/5 — deploying app"
docker compose up -d --remove-orphans --no-deps app

# host-side container metrics exporter (no-op when already running)
"$ROOT/scripts/host-metrics.sh" up >/dev/null 2>&1 || log "WARN: host-metrics exporter not running (make host-metrics-up)"

# ---------- stage 5: health ----------
log "stage 5/5 — waiting for $HEALTH_URL (max ${HEALTH_TIMEOUT}s)"
healthy=false
for _ in $(seq 1 $((HEALTH_TIMEOUT / 2))); do
  if curl -sf -m 2 "$HEALTH_URL" >/dev/null 2>&1; then
    healthy=true
    break
  fi
  sleep 2
done

if [ "$healthy" = true ]; then
  log "✅ deploy OK — $IMAGE:$SHA is serving $HEALTH_URL"
  log "    Grafana: https://grafana.tavesglobal.com | log: $LOG"
  exit 0
fi

# ---------- rollback ----------
log "❌ app unhealthy after ${HEALTH_TIMEOUT}s — rolling back"
docker compose logs --tail=40 app || true
if docker image inspect "$IMAGE:previous" >/dev/null 2>&1; then
  docker tag "$IMAGE:previous" "$IMAGE:latest"
  docker compose up -d --no-deps app
  log "rolled back to $IMAGE:previous"
else
  log "no previous image available — manual intervention needed"
fi
exit 1
