from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.database import get_db
from app.domains.auth.models import User
from app.domains.points import controller
from app.domains.points.schemas import PointLeaderboardMeRead
from app.utils.deps import get_current_user

router = APIRouter(prefix="/leaderboard", tags=["points"])


@router.get("/me", response_model=PointLeaderboardMeRead)
async def get_my_leaderboard_rank_compat(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await controller.leaderboard_me(db, user=user)
