import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import User
from app.domains.auth.schemas import UserCreate, UserUpdate
from app.domains.auth.service import delete_user_as_admin, get_user_for_view, list_users_for_admin, update_user_as_admin
from app.domains.auth.service.user_service import register_user


async def create_user(payload: UserCreate, db: AsyncSession) -> User:
    return await register_user(email=payload.email, username=payload.username, password=payload.password, db=db)


async def list_users(db: AsyncSession, *, skip: int = 0, limit: int = 20) -> list[User]:
    return await list_users_for_admin(db, skip=skip, limit=limit)


async def get_user(user_id: uuid.UUID, current_user: User, db: AsyncSession) -> User:
    return await get_user_for_view(db, user_id=user_id, current_user=current_user)


async def update_user(user_id: uuid.UUID, payload: UserUpdate, db: AsyncSession) -> User:
    return await update_user_as_admin(db, user_id=user_id, payload=payload)


async def delete_user(user_id: uuid.UUID, db: AsyncSession) -> None:
    await delete_user_as_admin(db, user_id=user_id)
