from hashlib import sha256

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.crud import get_role_by_name, get_user_by_username
from app.domains.auth.models import Role, User


def hash_password(password: str) -> str:
    return sha256(password.encode()).hexdigest()


async def get_role_or_500(db: AsyncSession, role_name: str) -> Role:
    role = await get_role_by_name(db, role_name)
    if not role:
        raise HTTPException(status_code=500, detail=f"Role '{role_name}' is not configured")
    return role


async def get_user_role_name(db: AsyncSession, user: User) -> str:
    if user.role:
        return user.role.name
    if not user.role_id:
        raise HTTPException(status_code=500, detail="User has no assigned role")
    role = await db.get(Role, user.role_id)
    if not role:
        raise HTTPException(status_code=500, detail="User role not found")
    return role.name


async def build_unique_username(db: AsyncSession, base: str) -> str:
    username, counter = base, 1
    while await get_user_by_username(db, username):
        username = f"{base}{counter}"
        counter += 1
    return username
