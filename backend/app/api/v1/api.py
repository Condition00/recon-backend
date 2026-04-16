from fastapi import APIRouter

from app.domains.auth.router import router as auth_router
from app.domains.incidents.router import router as incident_router
from app.domains.participants.router import router as participants_router
from app.infrastructure.storage.router import router as r2_router
from app.partners.router import router as partners_router
from app.domains.shop.router import router as shop_router
from app.domains.schedule.router.schedule_router import router as schedule_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(incident_router)
router.include_router(participants_router)
router.include_router(r2_router)
router.include_router(partners_router)
router.include_router(shop_router)
router.include_router(schedule_router)
