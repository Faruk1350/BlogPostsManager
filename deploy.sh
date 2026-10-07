#!/usr/bin/env bash
#
# One-command deployment for Blog Posts Manager.
#
#   ./deploy.sh            build -> test -> deploy -> healthcheck (rollback on failure)
#   ./deploy.sh --pull     same, but git pull --ff-only first
#   ./deploy.sh --logs     follow app logs after a successful deploy
#   ./deploy.sh --help     show this help
#
set -euo pipefail
cd "$(dirname "$0")"

PULL=0
FOLLOW_LOGS=0
for arg in "$@"; do
  case "$arg" in
    --pull) PULL=1 ;;
    --logs) FOLLOW_LOGS=1 ;;
    -h|--help)
      sed -n '2,9p' "$0"
      exit 0
      ;;
    *)
      echo "unknown option: $arg (try --help)" >&2
      exit 2
      ;;
  esac
done

echo "== Blog Posts Manager — deploy =="

# ---------------- preflight ----------------
command -v docker >/dev/null 2>&1 || {
  echo "✗ docker not found in PATH"
  exit 1
}
docker info >/dev/null 2>&1 || {
  echo "✗ Docker daemon is not running — start it with: colima start"
  exit 1
}
[ -f .env ] || {
  echo "✗ .env is missing — copy .env.example to .env and fill in the values"
  exit 1
}

if [ "$PULL" = 1 ]; then
  echo "→ pulling latest code (git pull --ff-only)"
  git pull --ff-only
fi

# ---------------- pipeline ----------------
echo "→ running pipeline (full log: .pipeline/deploy-*.log)"
if ./scripts/deploy.sh; then
  echo
  echo "✅ deploy finished"
  echo "   app        https://blog.tavesglobal.com        (local: http://127.0.0.1:5055)"
  echo "   grafana    https://grafana.tavesglobal.com     (local: http://127.0.0.1:3000)"
  echo "   alerts     https://alerts.tavesglobal.com      (local: http://127.0.0.1:9093)"
  echo "   version    $(curl -s -m 3 http://127.0.0.1:5055/metrics 2>/dev/null | awk '/^blog_app_info_info/{print $2}' || echo '?')"
  [ "$FOLLOW_LOGS" = 1 ] && exec docker compose logs -f --tail=50 app
else
  STATUS=$?
  echo
  echo "✗ deploy failed — recent log:"
  ls -t .pipeline/deploy-*.log 2>/dev/null | head -1
  exit "$STATUS"
fi
