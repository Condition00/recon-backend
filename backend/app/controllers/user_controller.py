import uuid

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import (
    approve_user_as_admin,
    delete_user_as_admin,
    get_user_for_view,
    list_users_for_admin,
    reject_user_as_admin,
    register_user,
    submit_application_for_current_user,
    update_user_as_admin,
)


async def create_user(payload: UserCreate, db: AsyncSession) -> User:
    return await register_user(payload, db)


async def list_users(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 20,
) -> list[User]:
    return await list_users_for_admin(db, skip=skip, limit=limit)


async def get_user(
    user_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> User:
    return await get_user_for_view(db, user_id=user_id, current_user=current_user)


async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: AsyncSession,
) -> User:
    return await update_user_as_admin(db, user_id=user_id, payload=payload)


async def delete_user(user_id: uuid.UUID, db: AsyncSession) -> None:
    await delete_user_as_admin(db, user_id=user_id)


async def submit_application(current_user: User, form_response: dict, db: AsyncSession) -> User:
    resume_key = form_response.get("resume_file_key", "")
    expected_prefix = f"resumes/{current_user.id}/"
    if not resume_key.startswith(expected_prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume file key does not belong to this user.",
        )
    return await submit_application_for_current_user(db, current_user=current_user, form_response=form_response)


async def approve_user(user_id: uuid.UUID, db: AsyncSession) -> User:
    return await approve_user_as_admin(db, user_id=user_id)


async def reject_user(user_id: uuid.UUID, db: AsyncSession) -> User:
    return await reject_user_as_admin(db, user_id=user_id)
