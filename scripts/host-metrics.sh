#!/usr/bin/env bash
# Container metrics exporter (host-side).
#
# cAdvisor is not usable on macOS container runtimes, and Colima cannot share
# its Unix socket with containers, so this exporter runs on the host and talks
# to the Docker socket directly. Prometheus scrapes http://host.docker.internal:9417.
#
# Usage: scripts/host-metrics.sh {up|down|status|logs}
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
VENV="$ROOT/.venv-host"
LOG_DIR="$ROOT/.pipeline"
LOG="$LOG_DIR/host-metrics.log"
PID_FILE="$LOG_DIR/host-metrics.pid"

mkdir -p "$LOG_DIR"

docker_host() {
  docker context inspect --format '{{.Endpoints.docker.Host}}' 2>/dev/null || echo "unix:///var/run/docker.sock"
}

ensure_venv() {
  if [ ! -x "$VENV/bin/python" ]; then
    echo "[host-metrics] creating venv at $VENV"
    python3 -m venv "$VENV"
  fi
  if ! "$VENV/bin/python" -c "import docker, prometheus_client" >/dev/null 2>&1; then
    echo "[host-metrics] installing exporter dependencies"
    "$VENV/bin/pip" install --quiet --disable-pip-version-check "docker>=7,<8" "prometheus-client>=0.20"
  fi
}

is_running() {
  [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

case "${1:-status}" in
  prepare)
    ensure_venv
    echo "[host-metrics] venv ready at $VENV"
    ;;
  up)
    # Already serving (launchd agent or an ad-hoc run from a previous shell).
    if curl -sf -m 3 http://127.0.0.1:9417/metrics >/dev/null 2>&1; then
      echo "[host-metrics] already serving on 127.0.0.1:9417"
      exit 0
    fi
    if is_running; then
      echo "[host-metrics] already running (pid $(cat "$PID_FILE"))"
      exit 0
    fi
    if lsof -nP -iTCP:9417 -sTCP:LISTEN >/dev/null 2>&1; then
      echo "[host-metrics] port 9417 already in use by another process:" >&2
      lsof -nP -iTCP:9417 -sTCP:LISTEN >&2
      exit 1
    fi
    ensure_venv
    DOCKER_HOST="$(docker_host)" nohup "$VENV/bin/python" observability/docker-metrics/exporter.py \
      >>"$LOG" 2>&1 &
    echo $! >"$PID_FILE"
    for _ in $(seq 1 20); do
      if curl -sf -m 2 http://127.0.0.1:9417/metrics >/dev/null 2>&1; then
        echo "[host-metrics] up (pid $(cat "$PID_FILE")) — DOCKER_HOST=$(docker_host)"
        exit 0
      fi
      sleep 1
    done
    echo "[host-metrics] FAILED to start, see $LOG" >&2
    tail -n 20 "$LOG" >&2 || true
    exit 1
    ;;
  down)
    if is_running; then
      kill "$(cat "$PID_FILE")" && rm -f "$PID_FILE"
      echo "[host-metrics] stopped"
    else
      rm -f "$PID_FILE"
      echo "[host-metrics] not running"
    fi
    ;;
  status)
    if is_running && curl -sf -m 3 http://127.0.0.1:9417/metrics >/dev/null; then
      echo "[host-metrics] up (pid $(cat "$PID_FILE"))"
    else
      echo "[host-metrics] down"
      exit 1
    fi
    ;;
  logs)
    tail -f "$LOG"
    ;;
  *)
    echo "usage: $0 {prepare|up|down|status|logs}" >&2
    exit 2
    ;;
esac
