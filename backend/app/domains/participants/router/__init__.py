from fastapi import APIRouter

from app.domains.participants.router.participant_router import router as participant_router
from app.domains.participants.router.portal_router import router as portal_router

router = APIRouter()
router.include_router(participant_router)
router.include_router(portal_router)

__all__ = ["router"]
