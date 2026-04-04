from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import Role


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    return (await db.exec(select(Role).where(Role.name == name))).one_or_none()
