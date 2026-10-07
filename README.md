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

### Search & recommendations

- Search is **semantic**: every post gets a local ONNX text embedding
  (`fastembed`, bge-small, 384 dims) stored in Postgres via **pgvector**;
  queries are embedded and matched by cosine similarity, topped up with
  ranked full-text results (`tsvector`) as a fallback
- Related stories use vector similarity to the source post
- The "For you" feed builds a taste centroid from posts you liked/commented
  on and ranks by vector distance, with category/author affinity as fallback
- Everything runs locally on CPU — no external embedding API

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Plain-text health check (used by Docker and CI) |
| GET | `/api/health` | JSON health with Supabase connection status |
| POST | `/api/auth/signup` | Create an account (first account becomes admin) |
| POST | `/api/auth/login` | Sign in, returns access + refresh tokens |
| POST | `/api/auth/refresh` | Rotate the refresh token, new access token |
| POST | `/api/auth/logout` | Revoke the refresh token |
| GET | `/api/auth/me` | Current user, profile and preferences |
| PUT | `/api/auth/password` | Change password |
| GET | `/items` `/api/posts` | List / search posts (full-text `q`, category, sort, pagination) |
| POST | `/items` `/api/posts` | Create a post (auth; supports `status=draft`) |
| GET | `/api/posts/{id}` | Fetch one post (increments views) |
| PUT | `/api/posts/{id}` | Edit a post (author or admin) |
| DELETE | `/api/posts/{id}` | Delete a post (author or admin) |
| GET | `/api/posts/{id}/related` | Related stories (vector similarity) |
| GET | `/api/feed/recommended` | Personalised feed (taste-vector ranking) |
| POST | `/api/posts/{id}/like` | Toggle like / unlike (auth) |
| POST | `/api/posts/{id}/share` | Record a share (auth) |
| GET | `/api/posts/{id}/comments` | List comments (paginated) |
| POST | `/api/posts/{id}/comments` | Add a comment (auth) |
| DELETE | `/api/comments/{id}` | Delete a comment (author or admin) |
| GET | `/api/profiles` | List profiles |
| GET | `/api/profiles/{id or username}` | Profile details with stats |
| PUT | `/api/profiles/{id}` | Update a profile (owner or admin) |
| GET | `/api/me` | Own user + profile + preferences |
| PUT | `/api/me` | Update own profile |
| GET/PUT | `/api/me/preferences` | Read / update theme, notifications, categories |
| POST | `/api/upload` | Upload an image (auth) |
| GET | `/metrics` | Prometheus metrics |
| GET | `/docs` | Swagger UI |

### Authentication

- Custom JWT auth: access tokens (30 min) + revocable rotating refresh tokens (30 days)
- Passwords hashed with bcrypt; sessions survive reloads via stored refresh token
- The **first account created becomes the admin** and inherits the original demo author and its posts
- Users can only edit/delete their own posts, comments and profile; admins can moderate everything
- Preferences (theme, notifications, favourite categories, default sort, digest) are stored per user

### Configuration

Copy `.env.example` to `.env` and fill in the values:

```
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_KEY=<service-role-key>     # server-side only, never shipped to the browser
```

`make up` starts the app together with the full observability stack.

## Technologies Used

- Python, FastAPI, Pydantic, Uvicorn
- Supabase (hosted PostgreSQL + REST) with pgvector
- Local semantic embeddings via fastembed (ONNX, CPU)
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
./deploy.sh      # one-command deploy: build -> test -> deploy -> healthcheck (+ rollback)
                 #   --pull to update first, --logs to follow logs after
make up          # build + start app + monitoring stack
make tunnel-up   # expose blog/grafana/alerts.tavesglobal.com
```
