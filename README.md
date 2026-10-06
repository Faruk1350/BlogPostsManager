# Blog Posts Manager

## Practical 10 - End-to-End DevOps Pipeline

### Project Description

Blog Posts Manager is a FastAPI + React application for publishing and
interacting with blog posts. Content lives in Supabase (Postgres) — there is no
local database and no seed data in the repository.

Features:

- Publish and delete posts with cover images, categories and computed read time
- Like / unlike posts (per user, protected by a unique constraint)
- Comment on posts, with comment counts kept in sync
- Record shares per platform
- Author profiles with bios, avatars and aggregate statistics
- Image upload endpoint used for covers and avatars
- OpenAPI docs at `/docs`, Prometheus metrics at `/metrics`

### Architecture

- `app.py` — root entrypoint (`python app.py` or `uvicorn app:app`)
- `backend/` — FastAPI application: routes, models, Supabase service layer
- `frontend/` — React (Vite) single-page UI, built and served by FastAPI in production

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Plain-text health check (used by Docker and CI) |
| GET | `/api/health` | JSON health with Supabase connection status |
| GET | `/items` `/api/posts` | List posts (search, category, sort, like detection) |
| POST | `/items` `/api/posts` | Create a post |
| GET | `/api/posts/{id}` | Fetch one post |
| DELETE | `/api/posts/{id}` | Delete a post (cascades likes/comments/shares) |
| POST | `/api/posts/{id}/like` | Toggle like / unlike |
| POST | `/api/posts/{id}/share` | Record a share |
| GET | `/api/posts/{id}/comments` | List comments |
| POST | `/api/posts/{id}/comments` | Add a comment |
| DELETE | `/api/comments/{id}` | Delete a comment |
| GET | `/api/profiles` | List profiles |
| GET | `/api/profiles/{id or username}` | Profile details with stats |
| PUT | `/api/profiles/{id}` | Update profile |
| GET | `/api/profiles/{id}/posts` | Posts by author |
| GET | `/api/profiles/{id}/likes` | Posts liked by author |
| POST | `/api/upload` | Upload an image (`jpg`, `jpeg`, `png`, `webp`, `gif`) |
| GET | `/metrics` | Prometheus metrics |
| GET | `/docs` | Swagger UI |

### Configuration

Copy `.env.example` to `.env` and fill in the values:

```
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_KEY=<service-role-key>     # server-side only, never shipped to the browser
```

`make up` starts the app together with the full observability stack.

## Technologies Used

- Python, FastAPI, Pydantic, Uvicorn
- Supabase (hosted PostgreSQL + REST)
- React 19, Vite
- Pytest, Docker, GitHub Actions
- Prometheus, Grafana, Loki, Alertmanager (see `OBSERVABILITY.md`)

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
