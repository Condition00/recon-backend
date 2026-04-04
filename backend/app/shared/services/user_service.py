import uuid
from hashlib import sha256

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.crud.role import get_role_by_name
from app.crud.user import create_user, delete_user, get_user_by_id, list_users
from app.models.role import ROLE_ADMIN, ROLE_APPLICANT, ROLE_PARTICIPANT
from app.models.user import STATUS_APPROVED, STATUS_PENDING, STATUS_REJECTED, User
from app.schemas.user import UserCreate, UserUpdate


def _hash_password(password: str) -> str:
    return sha256(password.encode()).hexdigest()


async def register_user(payload: UserCreate, db: AsyncSession) -> User:
    applicant_role = await get_role_or_500(db, ROLE_APPLICANT)
    user = await create_user(
        db,
        email=payload.email,
        username=payload.username,
        hashed_password=_hash_password(payload.password),
        role=applicant_role,
        status=None,
    )

    registered_user = await get_user_by_id(db, user.id, with_role=True)
    if not registered_user:
        raise HTTPException(status_code=500, detail="Failed to load created user")
    return registered_user


async def list_users_for_admin(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 20,
) -> list[User]:
    return await list_users(db, skip=skip, limit=limit)


async def get_user_for_view(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    current_user: User,
) -> User:
    current_role = current_user.role.name if current_user.role else None
    if current_role != ROLE_ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    user = await get_user_by_id(db, user_id, with_role=True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def update_user_as_admin(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: UserUpdate,
) -> User:
    user = await get_user_by_id(db, user_id, with_role=True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = payload.model_dump(exclude_unset=True)
    password = updates.pop("password", None)
    role_name = updates.pop("role_name", None)

    for field, value in updates.items():
        setattr(user, field, value)

    if password is not None:
        user.hashed_password = _hash_password(password)

    if role_name is not None:
        user.role = await get_role_or_500(db, role_name)

    await db.flush()
    await db.refresh(user)

    updated_user = await get_user_by_id(db, user.id, with_role=True)
    if not updated_user:
        raise HTTPException(status_code=500, detail="Failed to load updated user")
    return updated_user


async def delete_user_as_admin(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await delete_user(db, user)


async def submit_application_for_current_user(
    db: AsyncSession,
    *,
    current_user: User,
    form_response: dict,
) -> User:
    user = await get_user_by_id(db, current_user.id, with_role=True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status is not None:
        raise HTTPException(status_code=409, detail="Application already submitted")

    user.form_response = form_response
    user.status = STATUS_PENDING
    await db.flush()
    await db.refresh(user)

    submitted_user = await get_user_by_id(db, user.id, with_role=True)
    if not submitted_user:
        raise HTTPException(status_code=500, detail="Failed to load updated user")
    return submitted_user


async def approve_user_as_admin(db: AsyncSession, *, user_id: uuid.UUID) -> User:
    user = await get_user_by_id(db, user_id, with_role=True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.status = STATUS_APPROVED
    user.role = await get_role_or_500(db, ROLE_PARTICIPANT)
    await db.flush()
    await db.refresh(user)

    approved_user = await get_user_by_id(db, user.id, with_role=True)
    if not approved_user:
        raise HTTPException(status_code=500, detail="Failed to load updated user")
    return approved_user


async def reject_user_as_admin(db: AsyncSession, *, user_id: uuid.UUID) -> User:
    user = await get_user_by_id(db, user_id, with_role=True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.status = STATUS_REJECTED
    await db.flush()
    await db.refresh(user)

    rejected_user = await get_user_by_id(db, user.id, with_role=True)
    if not rejected_user:
        raise HTTPException(status_code=500, detail="Failed to load updated user")
    return rejected_user


async def get_role_or_500(db: AsyncSession, role_name: str):
    role = await get_role_by_name(db, role_name)
    if not role:
        raise HTTPException(status_code=500, detail=f"Role '{role_name}' is not configured")
    return role
