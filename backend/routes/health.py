from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from backend.supabase_client import is_supabase_configured

health_router = APIRouter(tags=["Health"])

@health_router.get("/health", response_class=PlainTextResponse)
def health_check():
    # Return "OK" for pytest and DevOps pipeline compatibility
    return "OK"

@health_router.get("/api/health")
def api_health():
    return {
        "status": "ok",
        "service": "Blog Posts Manager",
        "backend": "FastAPI",
        "database": "supabase" if is_supabase_configured() else "local_store",
        "supabase_connected": is_supabase_configured()
    }