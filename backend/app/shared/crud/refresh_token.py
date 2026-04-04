from sqlalchemy import update
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.refresh_token import RefreshToken


async def get_refresh_token_by_hash(
    db: AsyncSession,
    token_hash: str,
) -> RefreshToken | None:
    result = await db.exec(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    return result.one_or_none()


async def revoke_active_tokens_for_user(db: AsyncSession, user_id) -> None:
    await db.exec(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,
        )
        .values(is_revoked=True)
    )
