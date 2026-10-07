from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from backend import database
from backend.models import (
    PostResponse,
    PreferencesResponse,
    PreferencesUpdate,
    ProfileResponse,
    ProfileUpdate,
)
from backend.security import CurrentUser, assert_can_modify, get_current_user

profiles_router = APIRouter(prefix="/api/profiles", tags=["Profiles"])
me_router = APIRouter(prefix="/api/me", tags=["Me"])


# ----------------- Me (auth-scoped) -----------------

@me_router.get("")
def whoami(current: CurrentUser = Depends(get_current_user)):
    return {
        "user": {
            "id": current.id,
            "email": current.user["email"],
            "is_admin": current.is_admin,
        },
        "profile": current.profile,
        "preferences": PreferencesResponse(**database.get_preferences(current.id)),
    }


@me_router.put("", response_model=ProfileResponse)
def update_me(payload: ProfileUpdate, current: CurrentUser = Depends(get_current_user)):
    return database.update_profile(current.profile_id, payload.model_dump(exclude_unset=True))


@me_router.get("/preferences", response_model=PreferencesResponse)
def get_my_preferences(current: CurrentUser = Depends(get_current_user)):
    return database.get_preferences(current.id)


@me_router.put("/preferences", response_model=PreferencesResponse)
def update_my_preferences(
    payload: PreferencesUpdate, current: CurrentUser = Depends(get_current_user)
):
    return database.update_preferences(current.id, payload.model_dump(exclude_unset=True))


# ----------------- Public profiles -----------------

@profiles_router.get("", response_model=List[ProfileResponse])
def list_profiles():
    """List all available profiles."""
    return database.get_all_profiles()


@profiles_router.get("/{identifier}", response_model=ProfileResponse)
def get_profile(identifier: str):
    """Retrieve full profile details by ID or username."""
    profile = database.get_profile(identifier)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@profiles_router.put("/{profile_id}", response_model=ProfileResponse)
def update_profile(
    profile_id: str, updates: ProfileUpdate, current: CurrentUser = Depends(get_current_user)
):
    """Update a profile. Users may only edit their own; admins may edit any."""
    assert_can_modify(current, profile_id, "profile")

    if not database.get_profile(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")

    return database.update_profile(profile_id, updates.model_dump(exclude_unset=True))


@profiles_router.get("/{identifier}/posts", response_model=List[PostResponse])
def get_user_posts(
    identifier: str,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    viewer: CurrentUser = Depends(get_current_user),
):
    """Posts by this author: published for everyone, drafts for the owner/admin."""
    profile = database.get_profile(identifier)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    include_drafts = viewer.is_admin or viewer.profile_id == profile["id"]
    posts = database.get_posts(
        status="published" if not include_drafts else "draft",
        author_id=profile["id"],
        limit=limit,
        offset=offset,
        current_user_id=viewer.profile_id,
    )
    if include_drafts:
        posts = database.get_posts(
            status="published",
            author_id=profile["id"],
            limit=limit,
            offset=offset,
            current_user_id=viewer.profile_id,
        ) + posts
    return posts


@profiles_router.get("/{identifier}/likes", response_model=List[PostResponse])
def get_user_liked_posts(
    identifier: str,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    """Published posts liked by this profile."""
    profile = database.get_profile(identifier)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    posts = database.get_posts(limit=50, offset=0, current_user_id=profile["id"])
    return [post for post in posts if post.get("is_liked")][offset : offset + limit]
