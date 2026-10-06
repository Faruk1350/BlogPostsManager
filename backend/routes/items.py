from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend import database
from backend.models import (
    CommentCreate,
    CommentResponse,
    LikeResponse,
    LikeToggleRequest,
    PostCreate,
    PostResponse,
    PostUpdate,
    ShareRequest,
    ShareResponse,
)
from backend.security import CurrentUser, assert_can_modify, get_current_user, get_optional_user

posts_router = APIRouter(tags=["Posts & Interactions"])


def _visible(post: dict, viewer: Optional[CurrentUser]) -> bool:
    """Drafts are only visible to their author and admins."""
    if post.get("status", "published") == "published":
        return True
    if viewer is None:
        return False
    return viewer.is_admin or post.get("author_id") == viewer.profile_id


# ----------------- Posts -----------------

@posts_router.get("/items", response_model=List[PostResponse])
@posts_router.get("/api/posts", response_model=List[PostResponse])
def get_posts(
    q: Optional[str] = Query(None, description="Full-text search query (ranked)"),
    search: Optional[str] = Query(None, description="Legacy substring search"),
    category: Optional[str] = Query(None, description="Filter by category"),
    sort: str = Query("recent", pattern="^(recent|likes)$"),
    status_filter: str = Query("published", alias="status", pattern="^(published|draft)$"),
    author_id: Optional[str] = Query(None, description="Filter by author profile id"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    viewer: Optional[CurrentUser] = Depends(get_optional_user),
):
    """List or search posts. `status=draft` returns your own drafts only."""
    if status_filter == "draft":
        if viewer is None:
            raise HTTPException(status_code=401, detail="Sign in to view drafts")
        author_id = viewer.profile_id if not viewer.is_admin else author_id

    return database.get_posts(
        search=search,
        category=category,
        sort=sort,
        q=q,
        status="published" if status_filter == "published" and q else status_filter,
        author_id=author_id,
        limit=limit,
        offset=offset,
        current_user_id=viewer.profile_id if viewer else None,
    )


@posts_router.get("/api/feed/recommended", response_model=List[PostResponse])
def recommended_feed(
    limit: int = Query(20, ge=1, le=50),
    viewer: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Personalised feed when signed in, trending posts otherwise."""
    return database.get_recommended_posts(viewer.profile_id if viewer else None, limit=limit)


@posts_router.get("/api/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int, viewer: Optional[CurrentUser] = Depends(get_optional_user)):
    post = database.get_post_by_id(post_id, current_user_id=viewer.profile_id if viewer else None)
    if not post or not _visible(post, viewer):
        raise HTTPException(status_code=404, detail="Post not found")
    database.increment_views(post_id)
    post["views_count"] = (post.get("views_count") or 0) + 1
    return post


@posts_router.get("/api/posts/{post_id}/related", response_model=List[PostResponse])
def related_posts(post_id: int, limit: int = Query(5, ge=1, le=10)):
    return database.get_related_posts(post_id, limit=limit)


@posts_router.post("/items", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
@posts_router.post("/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(payload: PostCreate, current: CurrentUser = Depends(get_current_user)):
    if not payload.title.strip() or not payload.content.strip():
        raise HTTPException(status_code=400, detail="Title and content are required.")
    if payload.status == "draft" and not payload.title.strip():
        raise HTTPException(status_code=400, detail="Drafts still need a title.")

    post = database.create_post(
        {
            "title": payload.title.strip(),
            "content": payload.content,
            "cover_image": payload.cover_image,
            "category": payload.category,
            "status": payload.status or "published",
            "author_id": current.profile_id,
        }
    )
    return post


@posts_router.put("/api/posts/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int, payload: PostUpdate, current: CurrentUser = Depends(get_current_user)
):
    existing = database.get_post_by_id(post_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Post not found")
    assert_can_modify(current, existing.get("author_id"), "posts")

    updated = database.update_post(post_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Post not found")
    return updated


@posts_router.delete("/api/posts/{post_id}")
def delete_post(post_id: int, current: CurrentUser = Depends(get_current_user)):
    existing = database.get_post_by_id(post_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Post not found")
    assert_can_modify(current, existing.get("author_id"), "posts")

    if not database.delete_post(post_id):
        raise HTTPException(status_code=404, detail="Post not found or could not be deleted")
    return {"message": "Post deleted successfully", "id": post_id}


# ----------------- Likes -----------------

@posts_router.post("/api/posts/{post_id}/like", response_model=LikeResponse)
def toggle_like_post(
    post_id: int, payload: LikeToggleRequest, current: CurrentUser = Depends(get_current_user)
):
    post = database.get_post_by_id(post_id)
    if not post or not _visible(post, current):
        raise HTTPException(status_code=404, detail="Post not found")

    return database.toggle_like(post_id, current.profile_id)


# ----------------- Shares -----------------

@posts_router.post("/api/posts/{post_id}/share", response_model=ShareResponse)
def share_post(
    post_id: int, payload: ShareRequest, current: CurrentUser = Depends(get_current_user)
):
    post = database.get_post_by_id(post_id)
    if not post or not _visible(post, current):
        raise HTTPException(status_code=404, detail="Post not found")

    return database.record_share(post_id, payload.platform or "link", current.profile_id)


# ----------------- Comments -----------------

@posts_router.get("/api/posts/{post_id}/comments", response_model=List[CommentResponse])
def get_comments(
    post_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    viewer: Optional[CurrentUser] = Depends(get_optional_user),
):
    post = database.get_post_by_id(post_id)
    if not post or not _visible(post, viewer):
        raise HTTPException(status_code=404, detail="Post not found")
    return database.get_comments(post_id, limit=limit, offset=offset)


@posts_router.post(
    "/api/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    post_id: int, payload: CommentCreate, current: CurrentUser = Depends(get_current_user)
):
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Comment content cannot be empty.")

    post = database.get_post_by_id(post_id)
    if not post or not _visible(post, current):
        raise HTTPException(status_code=404, detail="Post not found")

    return database.add_comment(post_id, {"content": payload.content.strip(), "author_id": current.profile_id})


@posts_router.delete("/api/comments/{comment_id}")
def delete_comment(comment_id: int, current: CurrentUser = Depends(get_current_user)):
    comment = database.get_comment_by_id(comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    assert_can_modify(current, comment.get("author_id"), "comments")

    if not database.delete_comment(comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"message": "Comment removed successfully", "id": comment_id}
