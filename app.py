"""Root entry point for Blog Posts Manager FastAPI application.

Supports running directly:
    python app.py
Or using uvicorn:
    uvicorn app:app --reload --port 5000
"""

import os
from backend.app import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("app:app", host=host, port=port, reload=True)