from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.role import Role


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    result = await db.exec(select(Role).where(Role.name == name))
    return result.one_or_none()


async def list_roles(db: AsyncSession) -> list[Role]:
    result = await db.exec(select(Role))
    return result.all()
