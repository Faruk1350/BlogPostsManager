#!/usr/bin/env bash
# Creates (or reuses) the Cloudflare tunnel for tavesglobal.com and writes its config.
# Idempotent: safe to run multiple times.
set -euo pipefail

TUNNEL_NAME="${TUNNEL_NAME:-blog}"
DOMAIN="${DOMAIN:-tavesglobal.com}"
APP_HOSTNAME="${APP_HOSTNAME:-blog.$DOMAIN}"
GRAFANA_HOSTNAME="${GRAFANA_HOSTNAME:-grafana.$DOMAIN}"
ALERTS_HOSTNAME="${ALERTS_HOSTNAME:-alerts.$DOMAIN}"
CONFIG="$HOME/.cloudflared/config-$TUNNEL_NAME.yml"
METRICS_ADDR="127.0.0.1:60123"

command -v cloudflared >/dev/null || { echo "cloudflared not found in PATH" >&2; exit 1; }
command -v jq >/dev/null || { echo "jq not found in PATH" >&2; exit 1; }

if ! cloudflared tunnel list --output json | jq -e --arg n "$TUNNEL_NAME" '.[] | select(.name == $n)' >/dev/null; then
  echo "[tunnel] creating tunnel '$TUNNEL_NAME'"
  cloudflared tunnel create "$TUNNEL_NAME"
else
  echo "[tunnel] tunnel '$TUNNEL_NAME' already exists"
fi

TUNNEL_ID="$(cloudflared tunnel list --output json | jq -r --arg n "$TUNNEL_NAME" '.[] | select(.name == $n) | .id')"
CRED_FILE="$HOME/.cloudflared/$TUNNEL_ID.json"
[ -f "$CRED_FILE" ] || { echo "[tunnel] credentials file missing: $CRED_FILE" >&2; exit 1; }

for host in "$APP_HOSTNAME" "$GRAFANA_HOSTNAME" "$ALERTS_HOSTNAME"; do
  echo "[tunnel] DNS route $host -> $TUNNEL_NAME"
  cloudflared tunnel route dns "$TUNNEL_NAME" "$host" 2>&1 | sed 's/^/    /' || true
done

cat >"$CONFIG" <<EOF
# Managed by BlogPostsManager/scripts/setup-tunnel.sh
tunnel: $TUNNEL_NAME
credentials-file: $CRED_FILE
metrics: $METRICS_ADDR

ingress:
  - hostname: $APP_HOSTNAME
    service: http://127.0.0.1:5055
  - hostname: $GRAFANA_HOSTNAME
    service: http://127.0.0.1:3000
  - hostname: $ALERTS_HOSTNAME
    service: http://127.0.0.1:9094
  - service: http_status:404
EOF

echo "[tunnel] wrote $CONFIG"
echo "[tunnel] start it with: make tunnel-up"
