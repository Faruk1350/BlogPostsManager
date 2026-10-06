import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from backend import database, metrics
from backend.database import DatabaseUnavailable
from backend.routes.health import health_router
from backend.routes.items import posts_router
from backend.routes.profiles import profiles_router
from backend.routes.upload import upload_router

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
UPLOAD_DIR = BASE_DIR / "uploads"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed gauges that only change on traffic (never block startup on the DB).
    try:
        database.refresh_post_count()
    except Exception:
        pass
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
app.include_router(posts_router)
app.include_router(profiles_router)
app.include_router(upload_router)

# ---------------- Frontend (production build) ----------------
if FRONTEND_DIST.is_dir():
    # Serve the built React app at "/" — API routes above take precedence.
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
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
