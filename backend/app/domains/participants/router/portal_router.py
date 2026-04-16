from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.domains.auth.models import User
from app.domains.participants.controller import get_dashboard
from app.domains.participants.schemas import ParticipantDashboardRead
from app.utils.deps import get_current_user

router = APIRouter(prefix="/me", tags=["participants"])


@router.get("/dashboard", response_model=ParticipantDashboardRead)
async def get_my_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await get_dashboard(db, user=user)
