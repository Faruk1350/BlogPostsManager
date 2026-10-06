import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from backend import database, embeddings, metrics
from backend.database import DatabaseUnavailable
from backend.routes.auth import auth_router
from backend.routes.health import health_router
from backend.routes.items import posts_router
from backend.routes.profiles import me_router, profiles_router
from backend.routes.upload import upload_router

logger = logging.getLogger("blog")

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
UPLOAD_DIR = BASE_DIR / "uploads"


def _warm_embeddings() -> None:
    """Load the ONNX embedding model and backfill missing vectors.

    Runs in a background thread so startup and requests are never blocked on
    a model download; search degrades to full-text until it finishes.
    """
    try:
        if not embeddings.warmup():
            return
        database.backfill_embeddings()
    except Exception as exc:  # pragma: no cover - environment dependent
        logger.warning("embedding warmup failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed gauges that only change on traffic (never block startup on the DB).
    try:
        database.refresh_post_count()
    except Exception:
        pass
    threading.Thread(target=_warm_embeddings, daemon=True).start()
    yield


app = FastAPI(
    title="Blog Posts Manager API",
    description="Modern, Asynchronous Blog API powered by FastAPI and Supabase",
    version="2.0.0",
    lifespan=lifespan,
)

metrics.app_info.info({"version": os.getenv("APP_VERSION", "dev")})

# CORS: the Vite dev server proxies requests, but keep it permissive for
# direct API consumers (mobile, curl, other origins).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- Cache headers ----------------
# Hashed build assets can be cached forever (at the Cloudflare edge and in the
# browser); HTML must always be revalidated so a deploy can never leave users
# on a stale index.html referencing old assets.
@app.middleware("http")
async def cache_control(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path

    if path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path.startswith("/uploads/"):
        response.headers["Cache-Control"] = "public, max-age=86400"
    elif path == "/" or path.endswith(".html"):
        response.headers["Cache-Control"] = "no-cache"

    return response


# ---------------- Error handling ----------------
@app.exception_handler(DatabaseUnavailable)
async def database_unavailable_handler(request: Request, exc: DatabaseUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


# ---------------- Metrics ----------------
# Exposes /metrics: request counter, latency histogram and in-progress gauge
# grouped by method, handler and status class, plus the business metrics
# registered in backend.metrics.
Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    excluded_handlers=["/metrics", "/health"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


# ---------------- Static files ----------------
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ---------------- Routers ----------------
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(me_router)
app.include_router(posts_router)
app.include_router(profiles_router)
app.include_router(upload_router)

# ---------------- Frontend (production build) ----------------
if FRONTEND_DIST.is_dir():
    # Hashed build assets are served as static files; every other path falls
    # back to index.html so client-side routes (/login, /settings, /search…)
    # work on a hard refresh.
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        candidate = (FRONTEND_DIST / full_path).resolve()
        if (
            full_path
            and str(candidate).startswith(str(FRONTEND_DIST.resolve()))
            and candidate.is_file()
        ):
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")

else:
    @app.get("/")
    def root():
        return {
            "message": "Welcome to Blog Posts Manager API",
            "documentation": "/docs",
            "status": "online",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
        reload=True,
    )
