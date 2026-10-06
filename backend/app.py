import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routes.health import health_router
from backend.routes.items import posts_router
from backend.routes.profiles import profiles_router
from backend.routes.upload import upload_router

app = FastAPI(
    title="Blog Posts Manager API",
    description="Modern, Asynchronous Blog API powered by FastAPI and Supabase",
    version="2.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Uploads Directory
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Register Routers
app.include_router(health_router)
app.include_router(posts_router)
app.include_router(profiles_router)
app.include_router(upload_router)

@app.get("/")
def root():
    return {
        "message": "Welcome to Blog Posts Manager API",
        "documentation": "/docs",
        "status": "online"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("backend.app:app", host=host, port=port, reload=True)