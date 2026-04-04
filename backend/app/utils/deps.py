from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from redis.asyncio import Redis

from app.core.security import get_current_user as _get_current_user_from_cookie
from app.db.database import get_db
from app.domains.auth.models import User, Role, ROLE_PARTICIPANT

DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def get_redis(request: Request) -> Redis:
    return request.app.state.redis


async def get_current_user(user: User = Depends(_get_current_user_from_cookie)) -> User:
    return user


def require_roles(*allowed_roles: str):
    allowed = set(allowed_roles)

    async def role_checker(user: User = Depends(get_current_user)) -> User:
        role_name = user.role.name if user.role else None
        if role_name not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return role_checker


async def get_or_create_dev_user(db: AsyncSession) -> User:
    user = await db.get(User, DEV_USER_ID)
    if not user:
        result = await db.exec(select(Role).where(Role.name == ROLE_PARTICIPANT))
        participant_role = result.one_or_none()
        if not participant_role:
            raise HTTPException(status_code=500, detail="Participant role is not configured")
        user = User(id=DEV_USER_ID, email="dev@localhost.test", username="dev_user", role_id=participant_role.id)
        db.add(user)
        await db.flush()
        await db.refresh(user)
    return user
