# Observability & Deployment

Full local observability for the Blog Posts Manager, exposed through a Cloudflare
tunnel on `tavesglobal.com`. Everything runs on this machine; nothing is pushed.

## Architecture

```
                        Cloudflare edge
                             │
                 cloudflared tunnel "blog" (host, launchd)
                 ┌───────────┼──────────────┐
                 ▼           ▼              ▼
   blog.tavesglobal.com  grafana.…   alerts.…
        127.0.0.1:5055    :3000        :9094 ── basic auth (caddy) ──> :9093
                 │           │              alertmanager
                 │           │                    ▲
                 ▼           ▼                    │
            ┌─────────┐  ┌─────────┐   ┌──────────┴────┐
            │ blog-app│  │ grafana │   │ prometheus    │──┐
            │ flask   │◄─┤ (dashb.)│◄──┤ rules+scrape  │  │ blackbox
            └────┬────┘  └─────────┘   └───────┬───────┘  │ node-exporter
                 │ /metrics                    │          │ host-metrics (host)
                 └─────────────────────────────┘          │ cloudflared metrics
                 │                                        │
                 ▼                                        ▼
            loki ◄── promtail ◄── /var/log/blog/{app,access,alerts}.log
                                 (shared docker volume)
```

- **app** — FastAPI + Uvicorn, instrumented with `prometheus-fastapi-instrumentator`
  (`/metrics`) plus business counters for posts/likes/comments/shares/uploads.
  The built React frontend is served by the same service at `/`; logs go to a
  shared docker volume.
- **prometheus** — scrapes app, node-exporter, blackbox probes, cloudflared,
  the host container-metrics exporter, and evaluates alerting/recording rules.
- **alertmanager** — routes alerts to a local webhook receiver; UI proxied by
  Caddy with basic auth.
- **grafana** — provisioned datasources + the `Blog Posts Manager — Full
  Observability` dashboard (templated, ~35 panels).
- **loki + promtail** — ships app/access/alert logs into Loki.
- **blackbox-exporter** — synthetic probes of the three public URLs.
- **node-exporter** — host (Colima VM) CPU/memory/disk/network.
- **host-metrics** — small host-side exporter that reads the Docker API
  (cAdvisor is not usable on macOS runtimes; Colima cannot share its socket
  into containers). Exports containers named `blog-*` by default; set
  `EXPORTER_CONTAINER_PREFIX=""` to export every container.
- **cloudflared** — host-side tunnel, metrics on `127.0.0.1:60123`.

## URLs

| Service | Local | Public (tunnel) |
|---|---|---|
| Blog app | http://127.0.0.1:5055 | https://blog.tavesglobal.com |
| Grafana | http://127.0.0.1:3000 | https://grafana.tavesglobal.com |
| Prometheus | http://127.0.0.1:9090 | — |
| Alertmanager | http://127.0.0.1:9093 | https://alerts.tavesglobal.com (basic auth) |
| Loki | http://127.0.0.1:3100 | — |
| Alert webhook | http://127.0.0.1:9099/alerts | — |

Local app runs on port **5055** because macOS AirPlay already occupies 5000.

Credentials live in `.env` (gitignored): `make creds` prints the Grafana
admin password and Alertmanager basic-auth user. Everything else is
unauthenticated on localhost only (all ports bind `127.0.0.1`).

## Commands

```bash
make up                 # build + start the full stack
make deploy             # test -> build -> deploy -> healthcheck -> rollback
make logs               # app logs
make ps                 # container status
make alert-test         # synthetic alert through Alertmanager -> webhook -> Loki
make creds              # print local credentials

make host-metrics-up    # start container metrics exporter (host process)
make tunnel-setup       # create tunnel + DNS for the three hostnames (idempotent)
make tunnel-up          # start tunnel
make tunnel-status      # process, connections, DNS, public endpoints
make agents-install     # launchd agents: tunnel + metrics auto-start on login

make hooks-install      # auto-deploy on git commit / merge
make hooks-uninstall    # disable auto-deploy
```

## Auto-deployment pipeline

`scripts/deploy.sh` is the single pipeline entrypoint:

1. **build** — builds the runtime image (frontend + backend) as
   `blog-app:<git-sha>` and tags `latest`; the previous `latest` is saved as
   `blog-app:previous`
2. **test** — runs `pytest` in the app container with the real `.env`
   (integration tests against Supabase, self-cleaning)
3. **dependencies** — `docker compose up -d` for the observability stack
4. **deploy** — recreates only the `app` container
5. **healthcheck** — polls `http://127.0.0.1:5055/health` for up to 90s;
   on failure it rolls back to `blog-app:previous` and exits non-zero

Triggers:
- `make deploy` (manual)
- `.githooks/post-commit` and `.githooks/post-merge` (after `make hooks-install`)
  — deploys in the background when app/Dockerfile/compose/observability/scripts
  files change; set `SKIP_AUTODEPLOY=1` on a commit to skip
- `.github/workflows/pipeline.yml` (created locally, **not pushed**) — test and
  build on push; deploy job for a self-hosted runner is included as a comment

Pipeline logs: `.pipeline/deploy-*.log`, single-flight lock in
`.pipeline/deploy.lock`.

## Alerts

Rules live in `observability/prometheus/rules/alerts.yml`; recording rules in
`recording.yml`. Notifications go to the local webhook receiver (JSON-lines at
`/var/log/blog/alerts.log`, also visible at http://127.0.0.1:9099/alerts and in
Loki). Alertmanager supervises grouping, inhibition and silences.

| Severity | Alerts |
|---|---|
| critical | AppDown, AppHighLatencyP99, HostDown, HostDiskSpaceCritical, TunnelNoConnections, BlackboxProbeFailed |
| warning | AppHighErrorRate, AppHighLatencyP95, AppHighMemory, AppLoginFailureSpike, HostHighCpu, HostHighMemory, HostHighLoad, HostDiskSpaceLow, HostDiskWillFillIn24h, ContainerRestartLoop, ContainerHighCpu, ContainerHighMemory, BlackboxProbeSlow, AlertmanagerDown, LokiDown, DockerMetricsExporterDown |
| info | AppNoTraffic |

Auth events (`blog_auth_events_total{action=…}`) cover signup, login, failed
login, logout, token refresh and password changes; the dashboard's Business
Metrics row shows failed logins and the alert fires above five failures in
15 minutes.

Test end-to-end delivery with `make alert-test`, then check the dashboard
"Alert history" panel or `curl http://127.0.0.1:9099/alerts`.

## Configuration notes

- **Port 5055**: macOS AirPlay holds 5000. Tunnel config maps
  `blog.tavesglobal.com` → `127.0.0.1:5055`.
- **Dashboard**: `observability/grafana/dashboards/blog-observability.json`,
  auto-provisioned into the `Blog` folder. Dashboard JSON is the source of
  truth; UI edits are disabled (`allowUiUpdates: false`).
- **Metrics accuracy**: Uvicorn runs a single worker (`--workers 1`) so
  Prometheus counters are not split across processes. FastAPI runs sync
  endpoints in a threadpool, so concurrency is unaffected.
- **cAdvisor**: unsupported on macOS container runtimes; replaced by
  `observability/docker-metrics/exporter.py` running on the host.
- **Redeploying Grafana provisioning changes**: `docker compose restart grafana`.

## Troubleshooting

```bash
make ps                       # is everything running?
make logs                     # app logs
make tunnel-status            # tunnel + DNS + public endpoints
curl -s localhost:9090/api/v1/rules | jq '.data.groups[].rules[].name'   # loaded rules
curl -s localhost:9417/metrics  # container exporter
docker compose logs grafana promtail loki alertmanager
```

- **Logs panel empty** — check `docker compose logs promtail`; the app writes to
  the `logs` volume (`docker compose exec app ls -l /var/log/blog`).
- **Tunnel 502** — target container down or wrong port; verify the local URL
  first, then `make tunnel-status`.
- **Alert not delivered** — `docker compose logs alert-webhook`; verify the
  Alertmanager route with `curl localhost:9093/api/v2/status`.
- **Stale metrics after container removal** — series are auto-removed by the
  exporter on the next cycle (15s).
