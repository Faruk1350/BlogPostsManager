"""Supabase-backed data access layer.

Every read and write goes to the Supabase Postgres database. There is no local
seed data and no silent in-memory fallback: when the database cannot be reached
the API fails loudly with a 503 instead of serving stale data.
"""

import logging
import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend import embeddings, metrics
from backend.supabase_client import is_supabase_configured, supabase

logger = logging.getLogger("blog.database")


class DatabaseUnavailable(RuntimeError):
    """Raised when Supabase is not configured or cannot be reached."""


# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------

def _db():
    if not is_supabase_configured():
        raise DatabaseUnavailable(
            "Database not configured: set SUPABASE_URL and SUPABASE_KEY"
        )
    return supabase


def _fail(action: str, exc: Exception) -> DatabaseUnavailable:
    logger.error("%s failed: %s", action, exc)
    return DatabaseUnavailable(f"{action} failed: {exc}")


def refresh_post_count() -> None:
    """Keep the posts gauge in sync. Metrics must never break a request."""
    try:
        result = _db().table("posts").select("id", count="exact").execute()
        metrics.posts_gauge.set(result.count or 0)
    except Exception:
        logger.debug("post count refresh failed", exc_info=True)


def calculate_read_time(content: str) -> str:
    words = len(content.split())
    minutes = max(1, math.ceil(words / 180))
    return f"{minutes} min read"


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:80] or "post"


def _unique_slug(title: str) -> str:
    """Deterministic, collision-free slug (appends a short suffix when taken)."""
    base = slugify(title)
    try:
        existing = _db().table("posts").select("id").eq("slug", base).limit(1).execute()
    except Exception:
        return base
    if not existing.data:
        return base
    return f"{base}-{uuid.uuid4().hex[:6]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Posts
# --------------------------------------------------------------------------

def _apply_embedding(payload: Dict[str, Any], title: str, content: str) -> None:
    """Attach a semantic embedding to a post payload when the model is available."""
    vectors = embeddings.embed_documents([embeddings.document_text(title, content)])
    if vectors:
        payload["embedding"] = embeddings.to_sql_vector(vectors[0])
        metrics.embedding_status.set(1)
        metrics.embedding_events.labels(operation="embedded").inc()
    else:
        metrics.embedding_status.set(0)


def backfill_embeddings(limit: int = 200) -> int:
    """Compute embeddings for posts missing one (startup + after model installs)."""
    if not embeddings.available():
        metrics.embedding_status.set(0)
        return 0

    try:
        result = (
            _db()
            .table("posts")
            .select("id,title,content")
            .is_("embedding", "null")
            .limit(limit)
            .execute()
        )
        rows = result.data or []
        if not rows:
            metrics.embedding_status.set(1)
            return 0

        vectors = embeddings.embed_documents(
            [embeddings.document_text(row["title"], row["content"]) for row in rows]
        )
        if not vectors:
            metrics.embedding_status.set(0)
            return 0

        updated = 0
        for row, vector in zip(rows, vectors):
            _db().table("posts").update(
                {"embedding": embeddings.to_sql_vector(vector)}
            ).eq("id", row["id"]).execute()
            updated += 1

        logger.info("embeddings_backfilled count=%s", updated)
        metrics.embedding_status.set(1)
        metrics.embedding_events.labels(operation="backfilled").inc(updated)
        return updated
    except Exception as exc:
        logger.warning("embedding backfill failed: %s", exc)
        metrics.embedding_status.set(0)
        return 0


def _liked_post_ids(user_id: Optional[str]) -> set:
    if not user_id:
        return set()
    try:
        result = _db().table("likes").select("post_id").eq("user_id", user_id).execute()
        return {row["post_id"] for row in (result.data or [])}
    except Exception:
        logger.debug("like lookup failed", exc_info=True)
        return set()


def get_posts(
    search: Optional[str] = None,
    category: Optional[str] = None,
    sort: str = "recent",
    current_user_id: Optional[str] = None,
    q: Optional[str] = None,
    status: str = "published",
    author_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List posts.

    - `q` runs ranked full-text search (Postgres tsvector).
    - `search` is kept for backwards compatibility (substring match).
    - Likes are embedded in the same PostgREST call (one round-trip).
    """
    limit = max(1, min(limit, 50))
    offset = max(0, offset)

    if q:
        return _hybrid_search(q, current_user_id, limit, offset)

    try:
        query = _db().table("posts").select("*, likes(user_id)")

        if status:
            query = query.eq("status", status)
        if category and category.lower() != "all":
            query = query.eq("category", category)
        if author_id:
            query = query.eq("author_id", author_id)
        if search:
            term = search.replace(",", "").replace("*", "")
            query = query.or_(
                f"title.ilike.*{term}*,content.ilike.*{term}*,author_name.ilike.*{term}*"
            )

        query = query.order("likes_count" if sort == "likes" else "created_at", desc=True)
        query = query.range(offset, offset + limit - 1)
        posts = query.execute().data or []

        for post in posts:
            likes = post.pop("likes", None) or []
            post["is_liked"] = (
                any(like.get("user_id") == current_user_id for like in likes)
                if current_user_id
                else False
            )

        return posts
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading posts", exc) from exc


def _semantic_search(
    query: str, current_user_id: Optional[str], limit: int, offset: int
) -> List[Dict[str, Any]]:
    vector = embeddings.embed_query(query)
    if not vector:
        return []

    try:
        result = _db().rpc(
            "semantic_search",
            {
                "p_query_embedding": embeddings.to_sql_vector(vector),
                "p_limit": limit,
                "p_offset": offset,
                "p_min_similarity": 0.3,
            },
        ).execute()
    except Exception as exc:
        logger.warning("semantic search failed: %s", exc)
        return []

    posts = result.data or []
    liked = _liked_post_ids(current_user_id)
    for post in posts:
        post.pop("similarity", None)
        post["is_liked"] = post["id"] in liked
    return posts


def _hybrid_search(
    query: str, current_user_id: Optional[str], limit: int, offset: int
) -> List[Dict[str, Any]]:
    """Exact keyword hits first, semantic (vector) matches filling the rest.

    Lexical matches are the strongest signal when a query contains a rare or
    quoted term; embeddings pick up meaning when words alone find nothing
    (e.g. "marine mammals" -> a post about whales).
    """
    text = _search_posts(query, current_user_id, limit, offset)
    semantic = _semantic_search(query, current_user_id, limit, offset)

    seen = set()
    merged: List[Dict[str, Any]] = []
    for post in text + semantic:
        if post["id"] in seen:
            continue
        seen.add(post["id"])
        merged.append(post)
        if len(merged) >= limit:
            break
    return merged


def _search_posts(q: str, current_user_id: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
    try:
        result = _db().rpc(
            "search_posts", {"p_query": q, "p_limit": limit, "p_offset": offset}
        ).execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Searching posts", exc) from exc

    posts = result.data or []
    liked = _liked_post_ids(current_user_id)
    for post in posts:
        post.pop("rank", None)
        post["is_liked"] = post["id"] in liked
    return posts


def get_post_by_id(post_id: int, current_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    try:
        result = (
            _db()
            .table("posts")
            .select("*, likes(user_id)")
            .eq("id", post_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        post = result.data[0]
        likes = post.pop("likes", None) or []
        post["is_liked"] = (
            any(like.get("user_id") == current_user_id for like in likes)
            if current_user_id
            else False
        )
        return post
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading post", exc) from exc


def get_related_posts(post_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    try:
        result = _db().rpc(
            "related_posts", {"source_id": post_id, "max_rows": limit}
        ).execute()
        return result.data or []
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading related posts", exc) from exc


def get_recommended_posts(profile_id: Optional[str], limit: int = 20) -> List[Dict[str, Any]]:
    """Personalised feed when signed in; trending posts for anonymous readers."""
    try:
        if profile_id:
            result = _db().rpc(
                "recommended_feed", {"p_profile_id": profile_id, "max_rows": limit}
            ).execute()
        else:
            result = (
                _db()
                .table("posts")
                .select("*")
                .eq("status", "published")
                .order("likes_count", desc=True)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading recommendations", exc) from exc

    liked = _liked_post_ids(profile_id)
    posts = result.data or []
    for post in posts:
        post["is_liked"] = post.get("id") in liked
    return posts


def increment_views(post_id: int) -> int:
    try:
        result = _db().rpc("increment_post_views", {"p_id": post_id}).execute()
        if isinstance(result.data, int):
            return result.data
        if isinstance(result.data, list) and result.data:
            first = result.data[0]
            return int(first.get("increment_post_views", 0)) if isinstance(first, dict) else int(first)
        return 0
    except Exception:
        logger.debug("view increment failed", exc_info=True)
        return 0


def create_post(data: Dict[str, Any]) -> Dict[str, Any]:
    author_id = data.get("author_id") or "user_admin"
    profile = get_profile(author_id) or {}
    now = _now()

    payload = {
        "title": data["title"],
        "content": data["content"],
        "cover_image": data.get("cover_image"),
        "category": data.get("category") or "General",
        "author_id": author_id,
        "author_name": data.get("author_name") or profile.get("display_name") or "Anonymous",
        "author_avatar": data.get("author_avatar") or profile.get("avatar_url"),
        "read_time": calculate_read_time(data.get("content", "")),
        "status": data.get("status") or "published",
        "slug": _unique_slug(data["title"]),
        "likes_count": 0,
        "comments_count": 0,
        "shares_count": 0,
        "views_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    _apply_embedding(payload, data["title"], data["content"])

    try:
        result = _db().table("posts").insert(payload).execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Creating post", exc) from exc

    if not result.data:
        raise DatabaseUnavailable("Creating post failed: insert returned no data")

    post = result.data[0]
    post["is_liked"] = False
    logger.info(
        "post_created id=%s status=%s title=%s author=%s",
        post["id"], post["status"], post["title"], post["author_name"],
    )
    metrics.post_events.labels(action="created").inc()
    refresh_post_count()
    return post


def update_post(post_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    updates = {key: value for key, value in data.items() if value is not None}
    if "content" in updates:
        updates["read_time"] = calculate_read_time(updates["content"])
    if "title" in updates:
        updates["slug"] = _unique_slug(updates["title"])
    if not updates:
        return get_post_by_id(post_id)

    # Re-embed when the text changes so semantic search stays accurate.
    if "title" in updates or "content" in updates:
        current = get_post_by_id(post_id)
        if current:
            _apply_embedding(
                updates,
                updates.get("title") or current["title"],
                updates.get("content") or current["content"],
            )

    updates["updated_at"] = _now()

    try:
        result = _db().table("posts").update(updates).eq("id", post_id).execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Updating post", exc) from exc

    if not result.data:
        return None

    logger.info("post_updated id=%s fields=%s", post_id, ",".join(updates.keys()))
    metrics.post_events.labels(action="updated").inc()
    return get_post_by_id(post_id)


def delete_post(post_id: int) -> bool:
    try:
        result = _db().table("posts").delete().eq("id", post_id).execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Deleting post", exc) from exc

    if not result.data:
        return False

    logger.info("post_deleted id=%s", post_id)
    metrics.post_events.labels(action="deleted").inc()
    refresh_post_count()
    return True


# --------------------------------------------------------------------------
# Likes
# --------------------------------------------------------------------------

def toggle_like(post_id: int, user_id: str) -> Dict[str, Any]:
    db = _db()
    try:
        existing = (
            db.table("likes").select("id").eq("post_id", post_id).eq("user_id", user_id).execute()
        )
        if existing.data:
            db.table("likes").delete().eq("post_id", post_id).eq("user_id", user_id).execute()
            action = "unlike"
        else:
            db.table("likes").insert({"post_id": post_id, "user_id": user_id}).execute()
            action = "like"

        count_result = (
            db.table("likes").select("id", count="exact").eq("post_id", post_id).execute()
        )
        likes_count = count_result.count or 0
        db.table("posts").update({"likes_count": likes_count}).eq("id", post_id).execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Toggling like", exc) from exc

    logger.info("like_%s post_id=%s user_id=%s likes_count=%s", action, post_id, user_id, likes_count)
    metrics.like_events.labels(action=action).inc()
    return {"post_id": post_id, "liked": action == "like", "likes_count": likes_count}


# --------------------------------------------------------------------------
# Shares
# --------------------------------------------------------------------------

def record_share(post_id: int, platform: str, user_id: str) -> Dict[str, Any]:
    db = _db()
    try:
        db.table("shares").insert(
            {"post_id": post_id, "platform": platform, "user_id": user_id}
        ).execute()
        count_result = (
            db.table("shares").select("id", count="exact").eq("post_id", post_id).execute()
        )
        shares_count = count_result.count or 0
        db.table("posts").update({"shares_count": shares_count}).eq("id", post_id).execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Recording share", exc) from exc

    logger.info("share_recorded post_id=%s platform=%s user_id=%s", post_id, platform, user_id)
    metrics.share_events.inc()
    return {
        "post_id": post_id,
        "platform": platform,
        "shares_count": shares_count,
        "share_url": f"/post/{post_id}",
    }


# --------------------------------------------------------------------------
# Comments
# --------------------------------------------------------------------------

def get_comments(post_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    try:
        result = (
            _db()
            .table("comments")
            .select("*")
            .eq("post_id", post_id)
            .order("created_at", desc=False)
            .range(max(0, offset), max(0, offset) + max(1, min(limit, 100)) - 1)
            .execute()
        )
        return result.data or []
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading comments", exc) from exc


def get_comment_by_id(comment_id: int) -> Optional[Dict[str, Any]]:
    try:
        result = (
            _db().table("comments").select("*").eq("id", comment_id).limit(1).execute()
        )
        return result.data[0] if result.data else None
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading comment", exc) from exc


def _refresh_comment_count(db, post_id: int) -> int:
    count_result = (
        db.table("comments").select("id", count="exact").eq("post_id", post_id).execute()
    )
    comments_count = count_result.count or 0
    db.table("posts").update({"comments_count": comments_count}).eq("id", post_id).execute()
    return comments_count


def add_comment(post_id: int, comment_data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    author_id = comment_data.get("author_id") or "user_admin"
    profile = get_profile(author_id) or {}

    payload = {
        "post_id": post_id,
        "author_id": author_id,
        "author_name": comment_data.get("author_name") or profile.get("display_name") or "Reader",
        "author_avatar": comment_data.get("author_avatar") or profile.get("avatar_url"),
        "content": comment_data["content"],
        "created_at": _now(),
    }

    try:
        result = db.table("comments").insert(payload).execute()
        if not result.data:
            raise DatabaseUnavailable("Adding comment failed: insert returned no data")
        comments_count = _refresh_comment_count(db, post_id)
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Adding comment", exc) from exc

    logger.info("comment_created id=%s post_id=%s author=%s", result.data[0]["id"], post_id, payload["author_name"])
    metrics.comment_events.labels(action="created").inc()
    comment = result.data[0]
    comment["comments_count"] = comments_count
    return comment


def delete_comment(comment_id: int) -> bool:
    db = _db()
    try:
        existing = db.table("comments").select("id,post_id").eq("id", comment_id).limit(1).execute()
        if not existing.data:
            return False

        post_id = existing.data[0]["post_id"]
        db.table("comments").delete().eq("id", comment_id).execute()
        _refresh_comment_count(db, post_id)
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Deleting comment", exc) from exc

    logger.info("comment_deleted id=%s post_id=%s", comment_id, post_id)
    metrics.comment_events.labels(action="deleted").inc()
    return True


# --------------------------------------------------------------------------
# Profiles
# --------------------------------------------------------------------------

def get_profile_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    try:
        result = (
            _db()
            .table("profile_stats")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading profile by user", exc) from exc


def username_exists(username: str) -> bool:
    try:
        result = (
            _db().table("profiles").select("id").eq("username", username).limit(1).execute()
        )
        return bool(result.data)
    except Exception:
        return False


def create_profile(
    profile_id: str,
    username: str,
    display_name: str,
    user_id: str,
    email: Optional[str] = None,
    avatar_url: Optional[str] = None,
    bio: str = "",
) -> Dict[str, Any]:
    payload = {
        "id": profile_id,
        "user_id": user_id,
        "username": username,
        "display_name": display_name,
        "email": email,
        "avatar_url": avatar_url,
        "bio": bio,
    }
    try:
        result = _db().table("profiles").insert(payload).execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Creating profile", exc) from exc

    if not result.data:
        raise DatabaseUnavailable("Creating profile failed: insert returned no data")
    logger.info("profile_created id=%s username=%s", profile_id, username)
    return get_profile(profile_id) or result.data[0]


def link_profile_to_user(
    profile_id: str, user_id: str, email: Optional[str] = None
) -> Dict[str, Any]:
    updates: Dict[str, Any] = {"user_id": user_id}
    if email:
        updates["email"] = email
    try:
        result = _db().table("profiles").update(updates).eq("id", profile_id).execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Linking profile", exc) from exc

    if not result.data:
        raise DatabaseUnavailable(f"Profile {profile_id} could not be linked")
    logger.info("profile_linked id=%s user_id=%s", profile_id, user_id)
    return get_profile(profile_id) or result.data[0]


def find_unlinked_profile_by_email(email: str) -> Optional[Dict[str, Any]]:
    try:
        result = (
            _db()
            .table("profiles")
            .select("*")
            .is_("user_id", "null")
            .eq("email", email)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Looking up profile by email", exc) from exc


def get_unlinked_profile_by_id(profile_id: str) -> Optional[Dict[str, Any]]:
    try:
        result = (
            _db()
            .table("profiles")
            .select("*")
            .is_("user_id", "null")
            .eq("id", profile_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Looking up unlinked profile", exc) from exc


def get_profile(identifier: str) -> Optional[Dict[str, Any]]:
    """Single round-trip: the profile_stats view computes post/like totals."""
    try:
        result = (
            _db()
            .table("profile_stats")
            .select("*")
            .or_(f"id.eq.{identifier},username.eq.{identifier}")
            .limit(1)
            .execute()
        )
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading profile", exc) from exc

    return result.data[0] if result.data else None


def get_all_profiles() -> List[Dict[str, Any]]:
    try:
        result = _db().table("profile_stats").select("*").execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading profiles", exc) from exc

    return result.data or []


def update_profile(profile_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {key: value for key, value in updates.items() if value is not None}
    db = _db()

    try:
        if cleaned:
            db.table("profiles").update(cleaned).eq("id", profile_id).execute()

        # Keep denormalised author fields in sync for existing content.
        if cleaned.get("display_name"):
            db.table("posts").update({"author_name": cleaned["display_name"]}).eq("author_id", profile_id).execute()
            db.table("comments").update({"author_name": cleaned["display_name"]}).eq("author_id", profile_id).execute()
        if cleaned.get("avatar_url"):
            db.table("posts").update({"author_avatar": cleaned["avatar_url"]}).eq("author_id", profile_id).execute()
            db.table("comments").update({"author_avatar": cleaned["avatar_url"]}).eq("author_id", profile_id).execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Updating profile", exc) from exc

    logger.info("profile_updated id=%s fields=%s", profile_id, ",".join(cleaned.keys()))
    metrics.profile_events.inc()
    return get_profile(profile_id)


# --------------------------------------------------------------------------
# Users & auth
# --------------------------------------------------------------------------

def count_users() -> int:
    try:
        result = _db().table("users").select("id", count="exact").execute()
        return result.count or 0
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Counting users", exc) from exc


def create_user(email: str, password_hash: str, is_admin: bool = False) -> Dict[str, Any]:
    payload = {"email": email.lower().strip(), "password_hash": password_hash, "is_admin": is_admin}
    try:
        result = _db().table("users").insert(payload).execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Creating user", exc) from exc

    if not result.data:
        raise DatabaseUnavailable("Creating user failed: insert returned no data")
    user = result.data[0]
    logger.info("user_created id=%s admin=%s", user["id"], user["is_admin"])
    metrics.auth_events.labels(action="signup").inc()
    return user


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    try:
        result = (
            _db()
            .table("users")
            .select("*")
            .eq("email", email.lower().strip())
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading user by email", exc) from exc


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    try:
        result = _db().table("users").select("*").eq("id", user_id).limit(1).execute()
        return result.data[0] if result.data else None
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading user", exc) from exc


def update_user_password(user_id: str, password_hash: str) -> bool:
    try:
        result = (
            _db().table("users").update({"password_hash": password_hash}).eq("id", user_id).execute()
        )
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Updating password", exc) from exc

    if result.data:
        logger.info("password_changed user_id=%s", user_id)
    return bool(result.data)


def delete_user(user_id: str) -> bool:
    """Used by tests for cleanup; cascades preferences and refresh tokens."""
    try:
        result = _db().table("users").delete().eq("id", user_id).execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Deleting user", exc) from exc
    return bool(result.data)


# --------------------------------------------------------------------------
# Refresh tokens
# --------------------------------------------------------------------------

def store_refresh_token(user_id: str, token_hash: str, expires_at: str) -> None:
    try:
        _db().table("refresh_tokens").insert(
            {"user_id": user_id, "token_hash": token_hash, "expires_at": expires_at}
        ).execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Storing refresh token", exc) from exc


def get_refresh_token(token_hash: str) -> Optional[Dict[str, Any]]:
    try:
        result = (
            _db()
            .table("refresh_tokens")
            .select("*")
            .eq("token_hash", token_hash)
            .is_("revoked_at", "null")
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading refresh token", exc) from exc


def revoke_refresh_token(token_hash: str) -> bool:
    try:
        result = (
            _db()
            .table("refresh_tokens")
            .update({"revoked_at": _now()})
            .eq("token_hash", token_hash)
            .is_("revoked_at", "null")
            .execute()
        )
        return bool(result.data)
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Revoking refresh token", exc) from exc


# --------------------------------------------------------------------------
# Preferences
# --------------------------------------------------------------------------

DEFAULT_PREFERENCES: Dict[str, Any] = {
    "theme": "system",
    "notify_likes": True,
    "notify_comments": True,
    "notify_shares": True,
    "favorite_categories": [],
    "default_sort": "recent",
    "digest_frequency": "off",
}


def get_preferences(user_id: str) -> Dict[str, Any]:
    """Return preferences, creating the default row on first access."""
    try:
        result = (
            _db().table("preferences").select("*").eq("user_id", user_id).limit(1).execute()
        )
        if result.data:
            return result.data[0]

        created = _db().table("preferences").insert({"user_id": user_id}).execute()
        if created.data:
            return created.data[0]
        return {"user_id": user_id, **DEFAULT_PREFERENCES}
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading preferences", exc) from exc


def update_preferences(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {key: value for key, value in updates.items() if value is not None}
    cleaned["updated_at"] = _now()
    try:
        result = (
            _db().table("preferences").update(cleaned).eq("user_id", user_id).execute()
        )
        if not result.data:
            get_preferences(user_id)  # ensure the row exists, then retry once
            result = _db().table("preferences").update(cleaned).eq("user_id", user_id).execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Updating preferences", exc) from exc

    logger.info("preferences_updated user_id=%s fields=%s", user_id, ",".join(cleaned.keys()))
    metrics.preference_events.inc()
    return result.data[0]


def delete_profile(profile_id: str) -> bool:
    """Used by tests for cleanup."""
    try:
        result = _db().table("profiles").delete().eq("id", profile_id).execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Deleting profile", exc) from exc
    return bool(result.data)
