from fastapi import APIRouter

from app.api.v1.routers import auth, r2, users

router = APIRouter()

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(r2.router)
