from datetime import datetime, timezone

from fastapi import HTTPException, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.crud.oauth_account import create_oauth_account, get_oauth_account
from app.crud.refresh_token import get_refresh_token_by_hash, revoke_active_tokens_for_user
from app.crud.role import get_role_by_name
from app.crud.user import create_user, get_user_by_email, get_user_by_id, get_user_by_username
from app.models.role import ROLE_APPLICANT, Role
from app.models.user import User


async def find_or_create_oauth_user(
    db: AsyncSession,
    *,
    provider: str,
    provider_user_id: str,
    email: str,
) -> User:
    applicant_role = await get_role_or_500(db, ROLE_APPLICANT)

    oauth_account = await get_oauth_account(
        db,
        provider=provider,
        provider_user_id=provider_user_id,
    )
    if oauth_account:
        user = await get_user_by_id(db, oauth_account.user_id, with_role=True)
        if user:
            return user

    user = await get_user_by_email(db, email, with_role=True)
    if user:
        if not user.role_id:
            user.role = applicant_role
            await db.flush()
        await create_oauth_account(
            db,
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=email,
        )
        return user

    username = await build_unique_username(db, email.split("@")[0])
    user = await create_user(
        db,
        email=email,
        username=username,
        role=applicant_role,
        status=None,
    )
    await create_oauth_account(
        db,
        user_id=user.id,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=email,
    )

    created_user = await get_user_by_id(db, user.id, with_role=True)
    if not created_user:
        raise HTTPException(status_code=500, detail="Failed to load authenticated user")
    return created_user


async def issue_user_tokens(user: User, response: Response, db: AsyncSession) -> None:
    role_name = await get_user_role_name(db, user)
    access_token = create_access_token(user.id, role_name)
    refresh_token = await create_refresh_token(user.id, db)
    set_auth_cookies(response, access_token, refresh_token)


async def refresh_user_session(
    db: AsyncSession,
    *,
    refresh_token_value: str | None,
    response: Response,
) -> User:
    if not refresh_token_value:
        raise HTTPException(status_code=401, detail="No refresh token")

    token_record = await get_refresh_token_by_hash(db, hash_token(refresh_token_value))
    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if token_record.is_revoked:
        await revoke_active_tokens_for_user(db, token_record.user_id)
        raise HTTPException(
            status_code=401,
            detail="Refresh token reuse detected — all sessions revoked",
        )

    if token_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    token_record.is_revoked = True

    user = await get_user_by_id(db, token_record.user_id, with_role=True)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    await issue_user_tokens(user, response, db)
    return user


async def logout_user_session(
    db: AsyncSession,
    *,
    refresh_token_value: str | None,
    response: Response,
) -> None:
    if refresh_token_value:
        token_record = await get_refresh_token_by_hash(db, hash_token(refresh_token_value))
        if token_record:
            token_record.is_revoked = True

    clear_auth_cookies(response)


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.MODE == "production",
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.MODE == "production",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


async def build_unique_username(db: AsyncSession, base_username: str) -> str:
    username = base_username
    counter = 1
    while await get_user_by_username(db, username):
        username = f"{base_username}{counter}"
        counter += 1
    return username


async def get_user_role_name(db: AsyncSession, user: User) -> str:
    if user.role:
        return user.role.name
    if not user.role_id:
        raise HTTPException(status_code=500, detail="User has no assigned role")

    role = await db.get(Role, user.role_id)
    if not role:
        raise HTTPException(status_code=500, detail="User role not found")
    return role.name


async def get_role_or_500(db: AsyncSession, role_name: str):
    role = await get_role_by_name(db, role_name)
    if not role:
        raise HTTPException(status_code=500, detail=f"Role '{role_name}' is not configured")
    return role
