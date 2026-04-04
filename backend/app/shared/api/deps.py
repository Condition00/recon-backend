"""Shared FastAPI dependencies."""

from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from redis.asyncio import Redis

from app.core.security import get_current_user as _get_current_user_from_cookie
from app.db.database import get_db
from app.models.role import ROLE_APPLICANT, Role
from app.models.user import User

# Re-export get_db for convenience
__all__ = ["get_db", "get_current_user", "get_redis", "require_roles"]

async def get_redis(request: Request) -> Redis:
    """FastAPI dependency to get the redis connection pool from the app state."""
    return request.app.state.redis

# Dev user ID â€” consistent across restarts for dev testing
DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def get_or_create_dev_user(db: AsyncSession) -> User:
    """Get or create a development test user."""
    user = await db.get(User, DEV_USER_ID)
    if not user:
        result = await db.exec(select(Role).where(Role.name == ROLE_APPLICANT))
        applicant_role = result.one_or_none()
        if not applicant_role:
            raise HTTPException(status_code=500, detail="Applicant role is not configured")

        user = User(
            id=DEV_USER_ID,
            email="dev@localhost.test",
            username="dev_user",
            role_id=applicant_role.id,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    return user


async def get_current_user(
    user: User = Depends(_get_current_user_from_cookie),
) -> User:
    """
    In production: delegates to cookie-based JWT auth from security module.
    In development: could be extended to auto-create a dev user if needed.
    """
    return user


def require_roles(*allowed_roles: str):
    """Build a dependency that restricts access to the given roles."""
    allowed = set(allowed_roles)

    async def role_checker(user: User = Depends(get_current_user)) -> User:
        role_name = user.role.name if user.role else None
        if role_name not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_checker
