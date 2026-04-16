from fastapi import APIRouter

from app.domains.points.router.leaderboard_router import router as leaderboard_router
from app.domains.points.router.point_router import router as point_router

router = APIRouter()
router.include_router(point_router)
router.include_router(leaderboard_router)

__all__ = ["router"]
