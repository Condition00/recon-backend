import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.db.database import get_db
from app.domains.auth.models import RefreshToken, Role, User


def create_access_token(user_id: uuid.UUID, role_name: str) -> str:
    """Create a short-lived JWT access token."""
    payload = {
        "sub": str(user_id),
        "role": role_name,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_access_token(token: str) -> dict:
    """Decode and validate an access JWT. Returns the payload or raises."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def hash_token(raw_token: str) -> str:
    """SHA-256 hash a raw token for safe storage in the database."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def create_refresh_token(user_id: uuid.UUID, db: AsyncSession) -> str:
    """
    Create a long-lived refresh token.
    Returns the RAW token (for the cookie).
    Stores only the SHA-256 HASH in the database.
    """
    raw_token = secrets.token_urlsafe(64)
    refresh = RefreshToken(
        user_id=user_id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh)
    await db.flush()
    return raw_token  # raw goes to cookie, hash stays in DB


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency — reads access token from httpOnly cookie, returns the user."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.exec(
        select(User)
        .options(joinedload(User.role))
        .where(User.id == uuid.UUID(user_id))
    )
    user = result.one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    if not user.role:
        raise HTTPException(status_code=401, detail="User role not found")

    return user
