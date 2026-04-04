"""Auth controller — delegates auth orchestration to services."""

from fastapi import Response
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.user import User
from app.services.auth_service import (
    find_or_create_oauth_user,
    issue_user_tokens,
    logout_user_session,
    refresh_user_session,
)


async def handle_oauth_callback(
    provider: str,
    provider_user_id: str,
    email: str,
    db: AsyncSession,
) -> User:
    return await find_or_create_oauth_user(
        db,
        provider=provider,
        provider_user_id=provider_user_id,
        email=email,
    )


async def issue_tokens(user: User, response: Response, db: AsyncSession) -> None:
    await issue_user_tokens(user, response, db)


async def handle_refresh(
    refresh_token_value: str | None,
    response: Response,
    db: AsyncSession,
) -> User:
    return await refresh_user_session(
        db,
        refresh_token_value=refresh_token_value,
        response=response,
    )


async def handle_logout(
    refresh_token_value: str | None,
    response: Response,
    db: AsyncSession,
) -> None:
    await logout_user_session(
        db,
        refresh_token_value=refresh_token_value,
        response=response,
    )
