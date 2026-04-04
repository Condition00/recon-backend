from fastapi import APIRouter

from app.domains.auth.router.auth_router import router as _auth_router
from app.domains.auth.router.user_router import router as _user_router

router = APIRouter()
router.include_router(_auth_router)
router.include_router(_user_router)
