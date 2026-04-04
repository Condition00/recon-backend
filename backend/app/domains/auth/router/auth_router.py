from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from app.core.config import settings
from app.core.oauth import oauth
from app.db.database import get_db
from app.domains.auth.controller.auth_controller import handle_logout, handle_oauth_callback, handle_refresh, issue_tokens
from app.domains.auth.models import User
from app.domains.auth.schemas import UserProfile
from app.utils.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google/login")
async def google_login(request: Request):
    return await oauth.google.authorize_redirect(request, settings.GOOGLE_REDIRECT_URI)


@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo") or await oauth.google.parse_id_token(token, nonce=None)
    if not user_info or not user_info.get("email"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Could not get user info from Google")
    user = await handle_oauth_callback(
        provider="google", provider_user_id=user_info["sub"], email=user_info["email"], db=db
    )
    redirect = RedirectResponse(url="/test.html", status_code=302)
    await issue_tokens(user, redirect, db)
    return redirect


@router.get("/me", response_model=UserProfile)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.post("/refresh")
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    user = await handle_refresh(request.cookies.get("refresh_token"), response, db)
    return {"status": "ok", "user_id": str(user.id)}


@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    await handle_logout(request.cookies.get("refresh_token"), response, db)
    return {"status": "logged_out"}
