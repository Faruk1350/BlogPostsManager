#!/usr/bin/env bash
# Stops the blog Cloudflare tunnel.
set -euo pipefail

LABEL="com.tavesglobal.blog-tunnel"
UID_N="$(id -u)"

if launchctl print "gui/$UID_N/$LABEL" >/dev/null 2>&1; then
  echo "[tunnel] unloading launchd agent"
  launchctl bootout "gui/$UID_N/$LABEL" 2>/dev/null || true
fi

if pgrep -f "cloudflared.*config-blog.yml" >/dev/null 2>&1; then
  pkill -f "cloudflared.*config-blog.yml" && echo "[tunnel] stopped"
else
  echo "[tunnel] not running"
fi
