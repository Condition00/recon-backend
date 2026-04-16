import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.zones import crud


async def get_checked_in_zone_summary(
    db: AsyncSession, *, participant_id: uuid.UUID
) -> tuple[int, list[uuid.UUID]]:
    checked_in_count = await crud.count_checked_in_zones_for_participant(
        db, participant_id=participant_id
    )
    checked_in_zone_ids = await crud.list_checked_in_zone_ids_for_participant(
        db, participant_id=participant_id
    )
    return checked_in_count, checked_in_zone_ids
