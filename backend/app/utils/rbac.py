from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.domains.auth.models import User, Role, ROLE_ADMIN, ROLE_PARTICIPANT, DEFAULT_ROLE_NAMES


async def ensure_default_roles_and_admins(db: AsyncSession) -> None:
    roles_by_name = await _ensure_roles(db)
    await _assign_default_role(db, roles_by_name[ROLE_PARTICIPANT])
    if not settings.BOOTSTRAP_ADMIN_EMAILS:
        return
    admin_role = roles_by_name[ROLE_ADMIN]
    result = await db.exec(select(User).where(User.email.in_(settings.BOOTSTRAP_ADMIN_EMAILS)))
    for user in result.all():
        user.role_id = admin_role.id


async def _ensure_roles(db: AsyncSession) -> dict[str, Role]:
    result = await db.exec(select(Role))
    roles = {role.name: role for role in result.all()}
    for role_name in DEFAULT_ROLE_NAMES:
        if role_name not in roles:
            role = Role(name=role_name)
            db.add(role)
            await db.flush()
            roles[role_name] = role
    return roles


async def _assign_default_role(db: AsyncSession, default_role: Role) -> None:
    result = await db.exec(select(User).where(User.role_id.is_(None)))
    for user in result.all():
        user.role_id = default_role.id
