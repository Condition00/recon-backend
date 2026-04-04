import uuid

from sqlalchemy import update
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import RefreshToken


async def get_refresh_token_by_hash(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    return (await db.exec(select(RefreshToken).where(RefreshToken.token_hash == token_hash))).one_or_none()


async def revoke_active_tokens_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.exec(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)  # noqa: E712
        .values(is_revoked=True)
    )
