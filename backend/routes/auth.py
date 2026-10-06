import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend import database, metrics
from backend.models import (
    LoginRequest,
    LogoutRequest,
    PasswordChange,
    PreferencesResponse,
    RefreshRequest,
    SignupRequest,
)
from backend.security import (
    ACCESS_TOKEN_MINUTES,
    CurrentUser,
    create_access_token,
    get_current_user,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    refresh_expiry_iso,
    verify_password,
)

logger = logging.getLogger("blog.auth")

auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,40}$")


def _public_user(user: dict) -> dict:
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "is_admin": bool(user.get("is_admin")),
        "created_at": user.get("created_at"),
    }


def _issue_refresh_token(user_id: str) -> str:
    token = new_refresh_token()
    database.store_refresh_token(user_id, hash_refresh_token(token), refresh_expiry_iso())
    return token


def _token_payload(user: dict, profile: dict) -> dict:
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_MINUTES * 60,
        "refresh_token": _issue_refresh_token(str(user["id"])),
        "user": _public_user(user),
        "profile": profile,
    }


def _unique_username(base: str) -> str:
    candidate = re.sub(r"[^a-z0-9_]", "_", base.lower()).strip("_")[:30] or "user"
    if len(candidate) < 3:
        candidate = f"user_{candidate}"
    username = candidate
    suffix = 1
    while database.username_exists(username):
        suffix += 1
        username = f"{candidate[:28]}_{suffix}"
    return username


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest):
    """Create an account. The first account becomes the admin and inherits the
    original demo author profile (and its posts)."""
    email = payload.email.lower().strip()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Please provide a valid email address")

    if database.get_user_by_email(email):
        metrics.auth_events.labels(action="signup_failed").inc()
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    is_first_user = database.count_users() == 0
    user = database.create_user(email, hash_password(payload.password), is_admin=is_first_user)

    # 1) Claim an existing demo profile with the same email, or
    # 2) if this is the very first account, inherit the demo admin identity,
    # 3) otherwise create a fresh profile.
    profile = database.find_unlinked_profile_by_email(email)
    if profile:
        profile = database.link_profile_to_user(profile["id"], str(user["id"]), email)
    elif is_first_user:
        admin_profile = database.get_unlinked_profile_by_id("user_admin")
        if admin_profile:
            profile = database.link_profile_to_user("user_admin", str(user["id"]), email)
    if not profile:
        display_name = (payload.display_name or email.split("@")[0]).strip()
        username = payload.username if payload.username and USERNAME_RE.match(payload.username) else _unique_username(display_name)
        profile = database.create_profile(
            profile_id=str(user["id"]),
            username=username,
            display_name=display_name,
            user_id=str(user["id"]),
            email=email,
        )

    database.get_preferences(str(user["id"]))  # materialise defaults
    logger.info("signup email=%s admin=%s profile=%s", email, is_first_user, profile["id"])
    return _token_payload(user, profile)


@auth_router.post("/login")
def login(payload: LoginRequest):
    email = payload.email.lower().strip()
    user = database.get_user_by_email(email)

    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        metrics.auth_events.labels(action="login_failed").inc()
        logger.warning("login_failed email=%s", email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    profile = database.get_profile_by_user_id(str(user["id"]))
    if not profile:
        raise HTTPException(status_code=409, detail="Account has no profile — contact an admin")

    metrics.auth_events.labels(action="login").inc()
    logger.info("login_ok email=%s", email)
    return _token_payload(user, profile)


@auth_router.post("/refresh")
def refresh(payload: RefreshRequest):
    row = database.get_refresh_token(hash_refresh_token(payload.refresh_token))
    if not row:
        raise HTTPException(status_code=401, detail="Refresh token is invalid or revoked")

    expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
    if expires_at <= datetime.now(timezone.utc):
        database.revoke_refresh_token(row["token_hash"])
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = database.get_user_by_id(str(row["user_id"]))
    profile = database.get_profile_by_user_id(str(row["user_id"])) if user else None
    if not user or not profile:
        raise HTTPException(status_code=401, detail="Account no longer exists")

    database.revoke_refresh_token(row["token_hash"])  # rotate on every use
    metrics.auth_events.labels(action="refresh").inc()
    return _token_payload(user, profile)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, current: CurrentUser = Depends(get_current_user)):
    if payload.refresh_token:
        database.revoke_refresh_token(hash_refresh_token(payload.refresh_token))
    metrics.auth_events.labels(action="logout").inc()
    logger.info("logout user_id=%s", current.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@auth_router.get("/me")
def me(current: CurrentUser = Depends(get_current_user)):
    return {
        "user": _public_user(current.user),
        "profile": current.profile,
        "preferences": PreferencesResponse(**database.get_preferences(current.id)),
    }


@auth_router.put("/password")
def change_password(payload: PasswordChange, current: CurrentUser = Depends(get_current_user)):
    if not verify_password(payload.current_password, current.user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    database.update_user_password(current.id, hash_password(payload.new_password))
    metrics.auth_events.labels(action="password_change").inc()
    return {"message": "Password updated"}
