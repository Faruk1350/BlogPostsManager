from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# Auth models
# --------------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    display_name: Optional[str] = Field(default=None, max_length=80)
    username: Optional[str] = Field(default=None, max_length=40)


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# --------------------------------------------------------------------------
# Profile models
# --------------------------------------------------------------------------

class ProfileBase(BaseModel):
    username: str
    display_name: str
    email: Optional[str] = None
    bio: Optional[str] = ""
    avatar_url: Optional[str] = ""
    cover_image: Optional[str] = None
    tagline: Optional[str] = None
    website: Optional[str] = ""
    location: Optional[str] = ""


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    cover_image: Optional[str] = None
    tagline: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None


class ProfileResponse(ProfileBase):
    id: str
    user_id: Optional[str] = None
    created_at: Optional[str] = None
    posts_count: int = 0
    likes_received: int = 0


# --------------------------------------------------------------------------
# Preferences models
# --------------------------------------------------------------------------

class PreferencesUpdate(BaseModel):
    theme: Optional[str] = Field(default=None, pattern="^(light|dark|system)$")
    notify_likes: Optional[bool] = None
    notify_comments: Optional[bool] = None
    notify_shares: Optional[bool] = None
    favorite_categories: Optional[List[str]] = None
    default_sort: Optional[str] = Field(default=None, pattern="^(recent|likes)$")
    digest_frequency: Optional[str] = Field(default=None, pattern="^(off|daily|weekly)$")


class PreferencesResponse(BaseModel):
    user_id: str
    theme: str = "system"
    notify_likes: bool = True
    notify_comments: bool = True
    notify_shares: bool = True
    favorite_categories: List[str] = []
    default_sort: str = "recent"
    digest_frequency: str = "off"


# --------------------------------------------------------------------------
# Comment models
# --------------------------------------------------------------------------

class CommentCreate(BaseModel):
    content: str
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    author_avatar: Optional[str] = None


class CommentResponse(BaseModel):
    id: int
    post_id: int
    author_id: Optional[str] = None
    author_name: str
    author_avatar: Optional[str] = None
    content: str
    created_at: str


# --------------------------------------------------------------------------
# Post models
# --------------------------------------------------------------------------

class PostCreate(BaseModel):
    title: str
    content: str
    cover_image: Optional[str] = None
    category: Optional[str] = "General"
    status: Optional[str] = Field(default="published", pattern="^(draft|published)$")
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    author_avatar: Optional[str] = None


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    cover_image: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(draft|published)$")


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
    views_count: int = 0
    status: str = "published"
    slug: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    is_liked: Optional[bool] = False


# --------------------------------------------------------------------------
# Action models
# --------------------------------------------------------------------------

class LikeToggleRequest(BaseModel):
    user_id: Optional[str] = None


class LikeResponse(BaseModel):
    post_id: int
    liked: bool
    likes_count: int


class ShareRequest(BaseModel):
    platform: Optional[str] = "link"
    user_id: Optional[str] = None


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
