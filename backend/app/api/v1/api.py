from fastapi import APIRouter

from app.domains.auth.router import router as auth_router
from app.domains.participants.router import router as participants_router
from app.infrastructure.storage.router import router as r2_router
from app.partners.router import router as partners_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(participants_router)
router.include_router(r2_router)
router.include_router(partners_router)
