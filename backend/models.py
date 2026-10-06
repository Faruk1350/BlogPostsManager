from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Profile Models
class ProfileBase(BaseModel):
    username: str
    display_name: str
    email: Optional[str] = None
    bio: Optional[str] = ""
    avatar_url: Optional[str] = ""
    website: Optional[str] = ""
    location: Optional[str] = ""

class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None

class ProfileResponse(ProfileBase):
    id: str
    created_at: Optional[str] = None
    posts_count: int = 0
    likes_received: int = 0

# Comment Models
class CommentCreate(BaseModel):
    content: str
    author_id: Optional[str] = "user_admin"
    author_name: Optional[str] = "Current User"
    author_avatar: Optional[str] = None

class CommentResponse(BaseModel):
    id: int
    post_id: int
    author_id: Optional[str] = None
    author_name: str
    author_avatar: Optional[str] = None
    content: str
    created_at: str

# Post Models
class PostCreate(BaseModel):
    title: str
    content: str
    cover_image: Optional[str] = None
    category: Optional[str] = "General"
    author_id: Optional[str] = "user_admin"
    author_name: Optional[str] = "Faruk Developer"
    author_avatar: Optional[str] = None

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    cover_image: Optional[str] = None
    category: Optional[str] = None

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    cover_image: Optional[str] = None
    category: str = "General"
    author_id: Optional[str] = None
    author_name: str
    author_avatar: Optional[str] = None
    read_time: str = "3 min read"
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    created_at: str
    is_liked: Optional[bool] = False

# Action Models
class LikeToggleRequest(BaseModel):
    user_id: Optional[str] = "user_admin"

class LikeResponse(BaseModel):
    post_id: int
    liked: bool
    likes_count: int

class ShareRequest(BaseModel):
    platform: Optional[str] = "link"
    user_id: Optional[str] = "user_admin"

class ShareResponse(BaseModel):
    post_id: int
    platform: str
    shares_count: int
    share_url: str

class HealthResponse(BaseModel):
    status: str
    service: str
    backend: str
    database: str
    active_profile: str
