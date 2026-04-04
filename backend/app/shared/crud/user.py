import uuid

from sqlalchemy.orm import joinedload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.role import Role
from app.models.user import User


async def get_user_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    with_role: bool = False,
) -> User | None:
    query = select(User).where(User.id == user_id)
    if with_role:
        query = query.options(joinedload(User.role))

    result = await db.exec(query)
    return result.one_or_none()


async def get_user_by_email(
    db: AsyncSession,
    email: str,
    *,
    with_role: bool = False,
) -> User | None:
    query = select(User).where(User.email == email)
    if with_role:
        query = query.options(joinedload(User.role))

    result = await db.exec(query)
    return result.one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.exec(select(User).where(User.username == username))
    return result.one_or_none()


async def list_users(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 20,
) -> list[User]:
    result = await db.exec(
        select(User)
        .options(joinedload(User.role))
        .offset(skip)
        .limit(limit)
    )
    return result.all()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    username: str,
    hashed_password: str | None = None,
    role: Role | None = None,
    status: str | None = None,
    user_id: uuid.UUID | None = None,
) -> User:
    user = User(
        id=user_id or uuid.uuid4(),
        email=email,
        username=username,
        hashed_password=hashed_password,
        status=status,
    )
    if role is not None:
        user.role = role

    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user: User) -> None:
    await db.delete(user)
