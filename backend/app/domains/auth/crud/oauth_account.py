import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import OAuthAccount


async def get_oauth_account(db: AsyncSession, *, provider: str, provider_user_id: str) -> OAuthAccount | None:
    return (await db.exec(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
    )).one_or_none()


async def create_oauth_account(
    db: AsyncSession, *, user_id: uuid.UUID, provider: str, provider_user_id: str, provider_email: str
) -> OAuthAccount:
    account = OAuthAccount(
        user_id=user_id, provider=provider,
        provider_user_id=provider_user_id, provider_email=provider_email,
    )
    db.add(account)
    await db.flush()
    return account
