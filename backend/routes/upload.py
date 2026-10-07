import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend import metrics
from backend.security import CurrentUser, get_current_user

upload_router = APIRouter(prefix="/api", tags=["Uploads"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

@upload_router.post("/upload")
async def upload_file(
    file: UploadFile = File(...), current: CurrentUser = Depends(get_current_user)
):
    """Upload an image file for blog posts or user avatars."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file extension. Allowed extensions are: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    dest_path = UPLOAD_DIR / unique_filename

    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    file_url = f"/uploads/{unique_filename}"
    metrics.upload_events.inc()
    return {
        "url": file_url,
        "filename": unique_filename,
        "size": dest_path.stat().st_size
    }
