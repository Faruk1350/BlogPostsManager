"""Supabase-backed data access layer.

Every read and write goes to the Supabase Postgres database. There is no local
seed data and no silent in-memory fallback: when the database cannot be reached
the API fails loudly with a 503 instead of serving stale data.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend import metrics
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


def _refresh_post_count() -> None:
    """Keep the posts gauge in sync. Metrics must never break a request."""
    try:
        result = _db().table("posts").select("id", count="exact").execute()
        metrics.posts_gauge.set(result.count or 0)
    except Exception:
        logger.debug("post count refresh failed", exc_info=True)


def _liked_post_ids(user_id: str) -> set:
    try:
        result = _db().table("likes").select("post_id").eq("user_id", user_id).execute()
        return {row["post_id"] for row in (result.data or [])}
    except Exception:
        logger.debug("like lookup failed", exc_info=True)
        return set()


def calculate_read_time(content: str) -> str:
    words = len(content.split())
    minutes = max(1, math.ceil(words / 180))
    return f"{minutes} min read"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Posts
# --------------------------------------------------------------------------

def get_posts(
    search: Optional[str] = None,
    category: Optional[str] = None,
    sort: str = "recent",
    current_user_id: str = "user_admin",
) -> List[Dict[str, Any]]:
    """Return posts with optional search, category filter and sorting."""
    try:
        query = _db().table("posts").select("*")

        if category and category.lower() != "all":
            query = query.eq("category", category)
        if search:
            term = search.replace(",", "").replace("*", "")
            query = query.or_(
                f"title.ilike.*{term}*,content.ilike.*{term}*,author_name.ilike.*{term}*"
            )

        query = query.order("likes_count" if sort == "likes" else "created_at", desc=True)
        posts = query.execute().data or []

        liked = _liked_post_ids(current_user_id)
        for post in posts:
            post["is_liked"] = post["id"] in liked

        _refresh_post_count()
        return posts
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading posts", exc) from exc


def get_post_by_id(post_id: int, current_user_id: str = "user_admin") -> Optional[Dict[str, Any]]:
    try:
        result = (
            _db().table("posts").select("*").eq("id", post_id).limit(1).execute()
        )
        if not result.data:
            return None
        post = result.data[0]
        liked = _liked_post_ids(current_user_id)
        post["is_liked"] = post["id"] in liked
        return post
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading post", exc) from exc


def create_post(data: Dict[str, Any]) -> Dict[str, Any]:
    author_id = data.get("author_id") or "user_admin"
    profile = get_profile(author_id) or {}

    payload = {
        "title": data["title"],
        "content": data["content"],
        "cover_image": data.get("cover_image"),
        "category": data.get("category") or "General",
        "author_id": author_id,
        "author_name": data.get("author_name") or profile.get("display_name") or "Anonymous",
        "author_avatar": data.get("author_avatar") or profile.get("avatar_url"),
        "read_time": calculate_read_time(data.get("content", "")),
        "likes_count": 0,
        "comments_count": 0,
        "shares_count": 0,
        "created_at": _now(),
    }

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
    logger.info("post_created id=%s title=%s author=%s", post["id"], post["title"], post["author_name"])
    metrics.post_events.labels(action="created").inc()
    _refresh_post_count()
    return post


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
    _refresh_post_count()
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

def get_comments(post_id: int) -> List[Dict[str, Any]]:
    try:
        result = (
            _db()
            .table("comments")
            .select("*")
            .eq("post_id", post_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading comments", exc) from exc


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

def _profile_with_stats(profile: Dict[str, Any], post_stats: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    stats = post_stats.get(profile["id"], {})
    profile = dict(profile)
    profile["posts_count"] = stats.get("posts_count", 0)
    profile["likes_received"] = stats.get("likes_received", 0)
    return profile


def _post_stats_by_author() -> Dict[str, Dict[str, int]]:
    stats: Dict[str, Dict[str, int]] = {}
    try:
        result = _db().table("posts").select("author_id,likes_count").execute()
    except Exception as exc:
        raise _fail("Loading profile stats", exc) from exc

    for row in result.data or []:
        author_id = row.get("author_id")
        if not author_id:
            continue
        entry = stats.setdefault(author_id, {"posts_count": 0, "likes_received": 0})
        entry["posts_count"] += 1
        entry["likes_received"] += row.get("likes_count") or 0
    return stats


def get_profile(identifier: str) -> Optional[Dict[str, Any]]:
    try:
        result = (
            _db()
            .table("profiles")
            .select("*")
            .or_(f"id.eq.{identifier},username.eq.{identifier}")
            .limit(1)
            .execute()
        )
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading profile", exc) from exc

    if not result.data:
        return None
    return _profile_with_stats(result.data[0], _post_stats_by_author())


def get_all_profiles() -> List[Dict[str, Any]]:
    try:
        result = _db().table("profiles").select("*").execute()
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise _fail("Loading profiles", exc) from exc

    stats = _post_stats_by_author()
    return [_profile_with_stats(profile, stats) for profile in (result.data or [])]


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
