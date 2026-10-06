# Blog Posts Manager

## Practical 10 - End-to-End DevOps Pipeline

### Project Description
Blog Posts Manager is a simple Flask REST API for managing blog posts.

The application uses in-memory data storage.

## API Endpoints

### GET /items
Returns all blog posts.

### POST /items
Adds a new blog post.

### GET /health
Checks whether the application is running.

## Technologies Used
- Python
- Flask
- Pytest
- Prometheus Flask Exporter

## R2 Role
Developer & Version Control

## Observability & Deployment

A full local observability stack (Prometheus, Grafana, Loki, Alertmanager,
blackbox probes), Cloudflare tunnel and the local auto-deploy pipeline are
documented in [OBSERVABILITY.md](OBSERVABILITY.md).

```bash
make up          # build + start app + monitoring stack
make deploy      # test -> build -> deploy -> healthcheck (+ rollback)
make tunnel-up   # expose blog/grafana/alerts.tavesglobal.com
```