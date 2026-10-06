SHELL := /usr/bin/env bash
COMPOSE := docker compose

.PHONY: help up down clean restart ps logs logs-all test build deploy \
        host-metrics-up host-metrics-down host-metrics-status \
        tunnel-setup tunnel-up tunnel-down tunnel-status \
        agents-install agents-uninstall hooks-install hooks-uninstall \
        alert-test urls open-grafana open-prometheus open-alerts creds

help: ## Show available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- stack
up: ## Build + start the full local stack (app + observability)
	$(COMPOSE) up -d --build

down: ## Stop the stack (keeps data volumes)
	$(COMPOSE) down

clean: ## Stop the stack AND delete all data volumes (prometheus/grafana/loki history)
	$(COMPOSE) down -v

restart: ## Restart the whole stack
	$(COMPOSE) restart

ps: ## Show container status
	$(COMPOSE) ps

logs: ## Follow app logs
	$(COMPOSE) logs -f --tail=100 app

logs-all: ## Follow logs of every service
	$(COMPOSE) logs -f --tail=50

# ---------------------------------------------------------------- pipeline
test: ## Run the test suite in Docker
	docker build --target test -t blog-app:test .

build: ## Build the runtime image
	docker build --target runtime -t blog-app:latest .

deploy: ## Full local pipeline: test -> build -> deploy -> healthcheck -> rollback
	./scripts/deploy.sh

hooks-install: ## Install git hooks for auto-deploy on commit/merge
	git config core.hooksPath .githooks
	chmod +x .githooks/* scripts/*.sh
	@echo "auto-deploy enabled (disable with: make hooks-uninstall)"

hooks-uninstall: ## Remove the auto-deploy git hooks
	git config --unset core.hooksPath || true
	@echo "auto-deploy disabled"

# ---------------------------------------------------------------- host agents
host-metrics-up: ## Start the container metrics exporter (host process)
	./scripts/host-metrics.sh up

host-metrics-down: ## Stop the container metrics exporter
	./scripts/host-metrics.sh down

host-metrics-status: ## Check the container metrics exporter
	./scripts/host-metrics.sh status

agents-install: ## Install launchd agents (tunnel + metrics, auto-start on login)
	./scripts/install-agents.sh install

agents-uninstall: ## Remove the launchd agents
	./scripts/install-agents.sh uninstall

# ---------------------------------------------------------------- tunnel
tunnel-setup: ## Create tunnel + DNS records for blog/grafana/alerts.tavesglobal.com
	./scripts/setup-tunnel.sh

tunnel-up: ## Start the Cloudflare tunnel
	./scripts/tunnel-up.sh

tunnel-down: ## Stop the Cloudflare tunnel
	./scripts/tunnel-down.sh

tunnel-status: ## Show tunnel process, connections, DNS and public endpoints
	./scripts/tunnel-status.sh

# ---------------------------------------------------------------- extras
alert-test: ## Fire a synthetic test alert through Alertmanager -> webhook -> Loki
	curl -sS -XPOST http://127.0.0.1:9093/api/v2/alerts \
	  -H 'Content-Type: application/json' \
	  -d '[{"labels":{"alertname":"PipelineTest","severity":"warning","service":"blog-app"},"annotations":{"summary":"Synthetic test alert","description":"Sent by make alert-test"}}]'
	@echo ""
	@echo "check: make logs | grep ALERT   (or http://127.0.0.1:9099/alerts)"

urls: ## Print all local + public URLs
	@echo "app         http://127.0.0.1:5055           https://blog.tavesglobal.com"
	@echo "grafana     http://127.0.0.1:3000           https://grafana.tavesglobal.com"
	@echo "prometheus  http://127.0.0.1:9090"
	@echo "alertmanager http://127.0.0.1:9093          https://alerts.tavesglobal.com"
	@echo "loki        http://127.0.0.1:3100"
	@echo "webhook     http://127.0.0.1:9099/alerts"
	@echo "metrics     http://127.0.0.1:9417/metrics"

creds: ## Print local credentials (from .env)
	@test -f .env && grep -E '^(GRAFANA_ADMIN_USER|GRAFANA_ADMIN_PASSWORD|ALERTMANAGER_AUTH_USER)=' .env | sed 's/^/  /' || echo "no .env — copy .env.example to .env"

open-grafana: ## Open local Grafana
	open http://127.0.0.1:3000

open-prometheus: ## Open local Prometheus
	open http://127.0.0.1:9090

open-alerts: ## Open local Alertmanager
	open http://127.0.0.1:9093
