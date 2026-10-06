#!/usr/bin/env bash
# Starts the blog Cloudflare tunnel (launchd agent if installed, otherwise nohup).
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
CONFIG="$HOME/.cloudflared/config-blog.yml"
LOG="$ROOT/.pipeline/tunnel.log"
LABEL="com.tavesglobal.blog-tunnel"
UID_N="$(id -u)"

[ -f "$CONFIG" ] || { echo "[tunnel] config not found — run: make tunnel-setup" >&2; exit 1; }
mkdir -p "$ROOT/.pipeline"

running() { pgrep -f "cloudflared.*config-blog.yml" >/dev/null 2>&1; }

if launchctl print "gui/$UID_N/$LABEL" >/dev/null 2>&1; then
  echo "[tunnel] launchd agent installed — restarting it"
  launchctl kickstart -k "gui/$UID_N/$LABEL"
elif running; then
  echo "[tunnel] already running (pid $(pgrep -f 'cloudflared.*config-blog.yml' | head -1))"
else
  echo "[tunnel] starting (nohup, log: $LOG)"
  nohup cloudflared --no-autoupdate tunnel --config "$CONFIG" run >>"$LOG" 2>&1 &
fi

for _ in $(seq 1 30); do
  if curl -sf -m 2 http://127.0.0.1:60123/ready >/dev/null 2>&1; then
    echo "[tunnel] ready (metrics on 127.0.0.1:60123)"
    exit 0
  fi
  sleep 1
done

echo "[tunnel] did not become ready in 30s — check $LOG" >&2
exit 1
