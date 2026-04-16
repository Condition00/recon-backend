from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import User
from app.domains.participants.crud import get_participant_by_user_id
from app.domains.participants.models import Participant


async def get_participant_for_user(db: AsyncSession, *, user: User) -> Participant | None:
    return await get_participant_by_user_id(db, user.id)
