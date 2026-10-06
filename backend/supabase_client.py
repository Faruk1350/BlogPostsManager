import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
# Load both root and backend .env if present
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

supabase = None
is_connected = False

def init_supabase():
    global supabase, is_connected
    if SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL.startswith("http"):
        try:
            from supabase import create_client
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            is_connected = True
            logger.info("Connected to Supabase at %s", SUPABASE_URL)
        except Exception as e:
            logger.warning("Failed to initialize Supabase client: %s. Using local store fallback.", e)
            supabase = None
            is_connected = False
    else:
        logger.info("Supabase credentials not configured. Operating in local in-memory/JSON store fallback.")
        supabase = None
        is_connected = False
    return supabase

init_supabase()

def is_supabase_configured() -> bool:
    return is_connected and (supabase is not None)