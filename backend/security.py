"""Authentication primitives: password hashing, JWTs, refresh tokens, guards."""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend import database

JWT_ALGORITHM = "HS256"
JWT_SECRET = os.getenv("JWT_SECRET", "")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "30"))

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "adm": bool(user.get("is_admin")),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_expiry_iso() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)).isoformat()


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


class CurrentUser:
    """Authenticated caller: user row + linked profile row."""

    def __init__(self, user: dict, profile: dict):
        self.user = user
        self.profile = profile

    @property
    def id(self) -> str:
        return str(self.user["id"])

    @property
    def profile_id(self) -> str:
        return self.profile["id"]

    @property
    def is_admin(self) -> bool:
        return bool(self.user.get("is_admin"))


def _load_user(payload: dict) -> Optional[CurrentUser]:
    user = database.get_user_by_id(payload["sub"])
    if not user:
        return None
    profile = database.get_profile_by_user_id(str(user["id"]))
    if not profile:
        return None
    return CurrentUser(dict(user), profile)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> CurrentUser:
    if credentials is None or not credentials.credentials:
        raise _unauthorized()

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise _unauthorized("Invalid or expired token")

    current = _load_user(payload)
    if not current:
        raise _unauthorized("Account no longer exists")
    return current


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[CurrentUser]:
    if credentials is None or not credentials.credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        return None
    try:
        return _load_user(payload)
    except database.DatabaseUnavailable:
        return None


def require_admin(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not current.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current


def assert_can_modify(current: CurrentUser, owner_profile_id: Optional[str], what: str) -> None:
    if current.is_admin or (owner_profile_id or "") == current.profile_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"You can only modify your own {what}",
    )
