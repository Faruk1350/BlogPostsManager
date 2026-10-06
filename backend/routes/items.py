from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional, List
from backend.models import (
    PostCreate, PostResponse, 
    CommentCreate, CommentResponse, 
    LikeToggleRequest, LikeResponse,
    ShareRequest, ShareResponse
)
from backend import database

posts_router = APIRouter(tags=["Posts & Interactions"])

# ----------------- Posts Endpoints -----------------

@posts_router.get("/items", response_model=List[PostResponse])
@posts_router.get("/api/posts", response_model=List[PostResponse])
def get_posts(
    search: Optional[str] = Query(None, description="Search term for title or content"),
    category: Optional[str] = Query(None, description="Filter by category"),
    sort: str = Query("recent", description="Sort by 'recent' or 'likes'"),
    current_user_id: str = Query("user_admin", description="Current user ID for like detection")
):
    """Retrieve all blog posts with optional filtering, search, and sorting."""
    return database.get_posts(search=search, category=category, sort=sort, current_user_id=current_user_id)

@posts_router.get("/api/posts/{post_id}", response_model=PostResponse)
def get_post(
    post_id: int, 
    current_user_id: str = Query("user_admin", description="Current user ID")
):
    """Retrieve a single blog post by its unique ID."""
    post = database.get_post_by_id(post_id, current_user_id=current_user_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@posts_router.post("/items", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
@posts_router.post("/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(payload: PostCreate):
    """Create a new blog post with title, content, cover image, category, and author."""
    if not payload.title.strip() or not payload.content.strip():
        raise HTTPException(status_code=400, detail="Title and content are required.")
    
    post = database.create_post(payload.model_dump())
    return post

@posts_router.delete("/api/posts/{post_id}")
def delete_post(post_id: int):
    """Delete a blog post by ID."""
    success = database.delete_post(post_id)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found or could not be deleted")
    return {"message": "Post deleted successfully", "id": post_id}

# ----------------- Likes Endpoints -----------------

@posts_router.post("/api/posts/{post_id}/like", response_model=LikeResponse)
def toggle_like_post(post_id: int, payload: LikeToggleRequest):
    """Toggle like or unlike for a blog post."""
    post = database.get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    user_id = payload.user_id or "user_admin"
    result = database.toggle_like(post_id, user_id)
    return result

# ----------------- Shares Endpoints -----------------

@posts_router.post("/api/posts/{post_id}/share", response_model=ShareResponse)
def share_post(post_id: int, payload: ShareRequest):
    """Record a share action for a post."""
    post = database.get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    platform = payload.platform or "link"
    user_id = payload.user_id or "user_admin"
    return database.record_share(post_id, platform, user_id)

# ----------------- Comments Endpoints -----------------

@posts_router.get("/api/posts/{post_id}/comments", response_model=List[CommentResponse])
def get_comments(post_id: int):
    """Retrieve all comments for a specific post."""
    post = database.get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return database.get_comments(post_id)

@posts_router.post("/api/posts/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(post_id: int, payload: CommentCreate):
    """Add a new comment to a post."""
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Comment content cannot be empty.")
    
    post = database.get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comment = database.add_comment(post_id, payload.model_dump())
    return comment

@posts_router.delete("/api/comments/{comment_id}")
def delete_comment(comment_id: int):
    """Delete a comment by ID."""
    success = database.delete_comment(comment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"message": "Comment removed successfully", "id": comment_id}