#!/usr/bin/env bash
# Installs (or removes) the two host-side launchd agents:
#   1. cloudflared tunnel for tavesglobal.com  (com.tavesglobal.blog-tunnel)
#   2. container metrics exporter              (com.tavesglobal.blog-host-metrics)
#
# Usage: scripts/install-agents.sh [install|uninstall]
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
ACTION="${1:-install}"
UID_N="$(id -u)"
AGENTS_DIR="$HOME/Library/LaunchAgents"
LOGS_DIR="$HOME/Library/Logs"
TUNNEL_LABEL="com.tavesglobal.blog-tunnel"
METRICS_LABEL="com.tavesglobal.blog-host-metrics"

mkdir -p "$AGENTS_DIR" "$LOGS_DIR"

bootout() {
  local label="$1"
  if launchctl print "gui/$UID_N/$label" >/dev/null 2>&1; then
    launchctl bootout "gui/$UID_N/$label" 2>/dev/null || true
    echo "[agents] unloaded $label"
  fi
}

if [ "$ACTION" = "uninstall" ]; then
  bootout "$TUNNEL_LABEL"
  bootout "$METRICS_LABEL"
  rm -f "$AGENTS_DIR/$TUNNEL_LABEL.plist" "$AGENTS_DIR/$METRICS_LABEL.plist"
  echo "[agents] removed plists. (Processes started with make tunnel-up/host-metrics-up are stopped separately.)"
  exit 0
fi

# ---------- prerequisites ----------
[ -f "$HOME/.cloudflared/config-blog.yml" ] || { echo "[agents] run 'make tunnel-setup' first" >&2; exit 1; }
"$ROOT/scripts/host-metrics.sh" prepare
"$ROOT/scripts/host-metrics.sh" down >/dev/null 2>&1 || true
DOCKER_HOST_VAL="$(docker context inspect --format '{{.Endpoints.docker.Host}}' 2>/dev/null || echo 'unix:///var/run/docker.sock')"
CLOUDFLARED_BIN="$(command -v cloudflared)"

# ---------- tunnel agent ----------
bootout "$TUNNEL_LABEL"
cat >"$AGENTS_DIR/$TUNNEL_LABEL.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$TUNNEL_LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$CLOUDFLARED_BIN</string>
        <string>--no-autoupdate</string>
        <string>tunnel</string>
        <string>--config</string>
        <string>$HOME/.cloudflared/config-blog.yml</string>
        <string>run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>$LOGS_DIR/blog-tunnel.log</string>
    <key>StandardErrorPath</key>
    <string>$LOGS_DIR/blog-tunnel.log</string>
</dict>
</plist>
EOF

# ---------- container metrics agent ----------
bootout "$METRICS_LABEL"
cat >"$AGENTS_DIR/$METRICS_LABEL.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$METRICS_LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$ROOT/.venv-host/bin/python</string>
        <string>$ROOT/observability/docker-metrics/exporter.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$ROOT</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>DOCKER_HOST</key>
        <string>$DOCKER_HOST_VAL</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>$LOGS_DIR/blog-host-metrics.log</string>
    <key>StandardErrorPath</key>
    <string>$LOGS_DIR/blog-host-metrics.log</string>
</dict>
</plist>
EOF

launchctl bootstrap "gui/$UID_N" "$AGENTS_DIR/$TUNNEL_LABEL.plist"
launchctl bootstrap "gui/$UID_N" "$AGENTS_DIR/$METRICS_LABEL.plist"

sleep 2
echo "[agents] installed:"
launchctl print "gui/$UID_N/$TUNNEL_LABEL" >/dev/null 2>&1 && echo "  ✓ $TUNNEL_LABEL" || echo "  ✗ $TUNNEL_LABEL"
launchctl print "gui/$UID_N/$METRICS_LABEL" >/dev/null 2>&1 && echo "  ✓ $METRICS_LABEL" || echo "  ✗ $METRICS_LABEL"
echo "[agents] logs: $LOGS_DIR/blog-*.log"
