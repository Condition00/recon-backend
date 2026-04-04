"""Auth router — thin HTTP layer, delegates all logic to auth_controller."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from app.controllers import auth_controller
from app.core.config import settings
from app.db.database import get_db
from app.core.oauth import oauth
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import UserProfile

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google/login")
async def google_login(request: Request):
    """Redirect the user to Google's OAuth consent screen."""
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle the OAuth callback from Google."""
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")

    if not user_info:
        # Fallback: decode the id_token manually
        user_info = await oauth.google.parse_id_token(token, nonce=None)

    if not user_info or not user_info.get("email"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Could not get user info from Google")

    # Controller handles account linking + user creation
    user = await auth_controller.handle_oauth_callback(
        provider="google",
        provider_user_id=user_info["sub"],
        email=user_info["email"],
        db=db,
    )

    # Controller issues tokens and sets cookies
    redirect = RedirectResponse(url="/test.html", status_code=302)
    await auth_controller.issue_tokens(user, redirect, db)
    return redirect


@router.get("/me", response_model=UserProfile)
async def get_me(user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return user


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Rotate the refresh token and issue a new access token."""
    refresh_token_value = request.cookies.get("refresh_token")
    user = await auth_controller.handle_refresh(refresh_token_value, response, db)
    return {"status": "ok", "user_id": str(user.id)}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Revoke the refresh token and clear auth cookies."""
    refresh_token_value = request.cookies.get("refresh_token")
    await auth_controller.handle_logout(refresh_token_value, response, db)
    return {"status": "logged_out"}
