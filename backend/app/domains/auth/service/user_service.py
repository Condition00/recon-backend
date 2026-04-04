import uuid

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.crud import create_user, delete_user, get_user_by_id, list_users
from app.domains.auth.models import User, ROLE_ADMIN, ROLE_PARTICIPANT
from app.domains.auth.schemas import UserUpdate
from app.domains.auth.service.helpers import get_role_or_500, hash_password


async def register_user(email: str, username: str, password: str, db: AsyncSession) -> User:
    participant_role = await get_role_or_500(db, ROLE_PARTICIPANT)
    user = await create_user(db, email=email, username=username,
                             hashed_password=hash_password(password), role=participant_role)
    registered = await get_user_by_id(db, user.id, with_role=True)
    if not registered:
        raise HTTPException(status_code=500, detail="Failed to load created user")
    return registered


async def list_users_for_admin(db: AsyncSession, *, skip: int = 0, limit: int = 20) -> list[User]:
    return await list_users(db, skip=skip, limit=limit)


async def get_user_for_view(db: AsyncSession, *, user_id: uuid.UUID, current_user: User) -> User:
    current_role = current_user.role.name if current_user.role else None
    if current_role != ROLE_ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    user = await get_user_by_id(db, user_id, with_role=True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def update_user_as_admin(db: AsyncSession, *, user_id: uuid.UUID, payload: UserUpdate) -> User:
    user = await get_user_by_id(db, user_id, with_role=True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updates = payload.model_dump(exclude_unset=True)
    password = updates.pop("password", None)
    role_name = updates.pop("role_name", None)
    for field, value in updates.items():
        setattr(user, field, value)
    if password is not None:
        user.hashed_password = hash_password(password)
    if role_name is not None:
        user.role = await get_role_or_500(db, role_name)
    await db.flush()
    updated = await get_user_by_id(db, user.id, with_role=True)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to load updated user")
    return updated


async def delete_user_as_admin(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await delete_user(db, user)
