#!/usr/bin/env bash
# Tunnel status: process, metrics readiness, DNS records, public endpoints.
set -euo pipefail

DOMAIN="${DOMAIN:-tavesglobal.com}"
HOSTS=(blog.tavesglobal.com grafana.tavesglobal.com alerts.tavesglobal.com)

echo "== process =="
if pgrep -f "cloudflared.*config-blog.yml" >/dev/null 2>&1; then
  echo "  running (pid $(pgrep -f 'cloudflared.*config-blog.yml' | tr '\n' ' '))"
else
  echo "  NOT running"
fi

echo "== tunnel connections =="
curl -sf -m 3 http://127.0.0.1:60123/metrics 2>/dev/null | grep '^cloudflared_tunnel_ha_connections' || echo "  metrics endpoint unavailable"

echo "== DNS =="
for host in "${HOSTS[@]}"; do
  printf '  %-30s %s\n' "$host" "$(dig +short "$host" | tr '\n' ' ')"
done

echo "== public endpoints =="
printf '  %-30s %s\n' "https://$HOSTS/health" "$(curl -s -o /dev/null -m 6 -w '%{http_code}' "https://${HOSTS[0]}/health" || echo fail)"
printf '  %-30s %s\n' "https://grafana.$DOMAIN/api/health" "$(curl -s -o /dev/null -m 6 -w '%{http_code}' "https://grafana.$DOMAIN/api/health" || echo fail)"
printf '  %-30s %s\n' "https://alerts.$DOMAIN/-/healthy" "$(curl -s -o /dev/null -m 6 -w '%{http_code}' "https://alerts.$DOMAIN/-/healthy" || echo fail)"
