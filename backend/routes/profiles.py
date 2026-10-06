from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from backend.models import ProfileResponse, ProfileUpdate, PostResponse
from backend import database

profiles_router = APIRouter(prefix="/api/profiles", tags=["Profiles"])

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
def update_profile(profile_id: str, updates: ProfileUpdate):
    """Update profile bio, display name, avatar, location, and website."""
    profile = database.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    updated = database.update_profile(profile_id, updates.model_dump(exclude_unset=True))
    return updated

@profiles_router.get("/{identifier}/posts", response_model=List[PostResponse])
def get_user_posts(identifier: str, current_user_id: str = Query("user_admin")):
    """Get all posts published by this specific profile."""
    profile = database.get_profile(identifier)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    all_posts = database.get_posts(current_user_id=current_user_id)
    return [p for p in all_posts if p.get("author_id") == profile["id"]]

@profiles_router.get("/{identifier}/likes", response_model=List[PostResponse])
def get_user_liked_posts(identifier: str, current_user_id: str = Query("user_admin")):
    """Get all posts liked by this specific profile."""
    profile = database.get_profile(identifier)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    all_posts = database.get_posts(current_user_id=current_user_id)
    # Check likes in database
    return [p for p in all_posts if p.get("is_liked")]
