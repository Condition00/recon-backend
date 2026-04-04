from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.oauth_account import OAuthAccount


async def get_oauth_account(
    db: AsyncSession,
    *,
    provider: str,
    provider_user_id: str,
) -> OAuthAccount | None:
    result = await db.exec(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
    )
    return result.one_or_none()


async def create_oauth_account(
    db: AsyncSession,
    *,
    user_id,
    provider: str,
    provider_user_id: str,
    provider_email: str,
) -> OAuthAccount:
    oauth_account = OAuthAccount(
        user_id=user_id,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=provider_email,
    )
    db.add(oauth_account)
    await db.flush()
    return oauth_account
