"""Local semantic embeddings with graceful degradation.

Uses fastembed (ONNX, CPU-only) with a small sentence-transformer model so
search and recommendations get real vector semantics without any external
API. If the model cannot be loaded (no network on first run, missing native
libs), every helper degrades to None and callers fall back to full-text
search / affinity ranking.
"""

import logging
import os
import threading
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("blog.embeddings")

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
CACHE_DIR_ENV = os.getenv("FASTEMBED_CACHE_PATH", "").strip()
DIMENSIONS = 384
DOCUMENT_CHARS = 1500
QUERY_CHARS = 400

_lock = threading.Lock()
_model = None
_failed = False
_cache_dir: Optional[str] = None


def _resolve_cache_dir() -> str:
    """Container path when writable, otherwise the user cache (local runs)."""
    global _cache_dir
    if _cache_dir:
        return _cache_dir
    if CACHE_DIR_ENV:
        _cache_dir = CACHE_DIR_ENV
    else:
        container_path = Path("/app/.models")
        try:
            container_path.mkdir(parents=True, exist_ok=True)
            _cache_dir = str(container_path)
        except OSError:
            fallback = Path.home() / ".cache" / "fastembed"
            fallback.mkdir(parents=True, exist_ok=True)
            _cache_dir = str(fallback)
    return _cache_dir


def _load_model():
    global _model, _failed
    if _model is not None or _failed:
        return _model
    with _lock:
        if _model is None and not _failed:
            try:
                from fastembed import TextEmbedding

                _model = TextEmbedding(model_name=MODEL_NAME, cache_dir=_resolve_cache_dir())
                logger.info("embedding model ready: %s (%sd)", MODEL_NAME, DIMENSIONS)
            except Exception as exc:  # pragma: no cover - environment dependent
                _failed = True
                logger.warning("embeddings unavailable, falling back to text search: %s", exc)
    return _model


def available() -> bool:
    return _load_model() is not None


def warmup() -> bool:
    """Load the model eagerly (used by the startup backfill thread)."""
    return available()


def embed_documents(texts: List[str]) -> Optional[List[List[float]]]:
    model = _load_model()
    if model is None or not texts:
        return None
    try:
        return [[float(value) for value in vector] for vector in model.embed(texts)]
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.warning("embedding documents failed: %s", exc)
        return None


def embed_query(text: str) -> Optional[List[float]]:
    model = _load_model()
    if model is None or not text.strip():
        return None
    try:
        vector = next(iter(model.query_embed([text[:QUERY_CHARS]])))
        return [float(value) for value in vector]
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.warning("embedding query failed: %s", exc)
        return None


def document_text(title: str, content: str) -> str:
    return f"{title}\n\n{content[:DOCUMENT_CHARS]}".strip()


def to_sql_vector(vector: List[float]) -> str:
    """PostgREST receives the vector as a text literal."""
    return "[" + ",".join(f"{value:.7f}" for value in vector) + "]"
